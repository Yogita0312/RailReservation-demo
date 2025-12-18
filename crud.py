from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_
from sqlalchemy import func
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from models import Train, RouteStation, Station, BerthClass, TrainSeatAvailability
from schemas import TrainAvailability, ClassAvailability
import unicodedata
import logging
import re

# ---------------- Logger Setup ----------------
logger = logging.getLogger("train_search")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
console_handler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(console_handler)

# ---------------- Normalize station names ----------------
def normalize(s: str):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s or "")
        if not unicodedata.combining(c)
    ).lower().strip()

# ---------------- Wildcard matcher helper function ----------------
def wildcard_match(text: str, pattern: str) -> bool:
    """
    Replicates SQL:
    lower(text) LIKE lower(replace(pattern, '?', '_'))
    """
    if not text or not pattern:
        return False

    # Escape regex special chars
    regex = re.escape(pattern)

    # SQL-style wildcards
    regex = regex.replace(r'\?', '.')   # ? -> single character
    regex = regex.replace(r'\%', '.*')  # % -> many characters

    return re.search(regex, text, re.IGNORECASE) is not None


# ---------------- Match station using name variants ----------------
def match_station(user_input: str, station: Station):
    norm_input = normalize(user_input)

    # 1. Exact match on primary fields
    if normalize(station.station_name) == norm_input:
        return True

    if normalize(station.station_name_PL) == norm_input:
        return True

    if normalize(station.station_id_code) == norm_input:
        return True

    # 2. Alias-based matching (controlled)
    if station.station_name_comb_PL:
        aliases = station.station_name_comb_PL.split("|")

        for alias in aliases:
            norm_alias = normalize(alias)

            # a) Exact alias match (preferred)
            if norm_alias == norm_input:
                return True

            # b) Wildcard match ONLY if user used wildcards
            if "?" in user_input or "%" in user_input:
                if wildcard_match(norm_alias, norm_input):
                    return True

    return False


# ---------------- Main search function ----------------
def search_trains(
    db: Session,
    from_station_name: str,
    to_station_name: str,
    travel_date: date,
    train_class: str, 
    time: str,
    train_name: str | None = None,
    train_number: str | None = None,
    train_type: str | None = None,
    return_date: date | None = None,
    return_time: str | None = None,
    return_train_class: str | None = None,
    return_train_number: str | None = None,
    return_train_name: str | None = None,
    return_train_type: str | None = None
    
):
    try:
        # ---------------- Validate Mandatory Fields ----------------
        if not from_station_name or from_station_name.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="From station is required and cannot be empty"
            )

        if not to_station_name or to_station_name.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="To station is required and cannot be empty"
            )

        if not travel_date:
            raise HTTPException(
                status_code=400,
                detail="Travel date is required"
            )

        if not train_class or train_class.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Train class is required and cannot be empty"
            )

        if not time or time.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Time is required and cannot be empty"
            )


        logger.info("🔥 search_trains called")
        logger.info(f"params: from={from_station_name} to={to_station_name} date={travel_date} time={time} train_number={train_number}")

        # ---------------- Get Stations ----------------
        stations = db.query(Station).all()

# Match by English OR Polish OR station code
        from_station = next(
            (s for s in stations if match_station(from_station_name, s)),
            None
        )

        to_station = next(
            (s for s in stations if match_station(to_station_name, s)),
            None
        )

        if not from_station:
            raise HTTPException(
                status_code=404,
                detail=f"From station '{from_station_name}' not found"
            )

        if not to_station:
            raise HTTPException(
                status_code=404,
                detail=f"To station '{to_station_name}' not found"
            )

        from_id = from_station.station_id
        to_id = to_station.station_id

        # ✅ Force Polish names for API output
        polish_from = from_station.station_name_PL
        polish_to = to_station.station_name_PL


        # ---------------- Find route_ids containing both stations in correct order ----------------
        rf = aliased(RouteStation)
        rt = aliased(RouteStation)
        route_rows = (
            db.query(rf.route_id)
            .join(rt, rf.route_id == rt.route_id)
            .filter(
                rf.station_id == from_id,
                rt.station_id == to_id,
                rf.stop_number < rt.stop_number
            )
            .distinct()
            .all()
        )
        route_ids = [r[0] for r in route_rows]
        if not route_ids:
            raise HTTPException(
                status_code=404,
                detail=f"There is no route between {polish_from} to {polish_to}"
            )
        # ---------------- Base Train Query ----------------
        trains_query = db.query(Train).filter(Train.route_id.in_(route_ids))
        if train_number:
            try:
                tn = int(train_number)
            except ValueError:
                raise HTTPException(400, "Train number must be numeric")

            # First check: train_no
            primary_match = trains_query.filter(Train.train_no == tn)

            if primary_match.count() > 0:
                trains_query = primary_match
            else:
                # Second check: alternate_train_no
                alternate_match = trains_query.filter(Train.alternate_train_no == tn)

                if alternate_match.count() > 0:
                    trains_query = alternate_match
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Train number {train_number} is not available for the route {polish_from} to {polish_to}"
                    )

        if train_name:
            normalized_train_name = normalize(train_name)
            train_name_exists = (
                trains_query
                .with_entities(Train.train_id)
                .filter(Train.train_name.ilike(f"%{normalized_train_name}%"))
                .first()
            )

            if not train_name_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Train name '{train_name}' not found"
                )

            trains_query = trains_query.filter(
                Train.train_name.ilike(f"%{normalized_train_name}%")
            )

        # Train type filter with validation
        if train_type:
            train_type_exists = (
                trains_query
                .with_entities(Train.train_id)
                .filter(Train.train_type.ilike(f"%{train_type}%"))
                .first()
            )

            if not train_type_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Train type '{train_type}' not found"
                )

            trains_query = trains_query.filter(
                Train.train_type.ilike(f"%{train_type}%")
            )

        # ---------------- Time-based nearest train filtering ----------------
        if time:
            input_t = datetime.strptime(time, "%H:%M").time()

            # 3 trains BEFORE input time
            before_trains = (
                trains_query
                .join(RouteStation, RouteStation.train_id == Train.train_id)
                .filter(
                    RouteStation.station_id == from_id,
                    RouteStation.departure_time < input_t
                )
                .order_by(RouteStation.departure_time.desc())
                .limit(3)
                .all()
            )

            # 3 trains AFTER (including equal time)
            after_trains = (
                trains_query
                .join(RouteStation, RouteStation.train_id == Train.train_id)
                .filter(
                    RouteStation.station_id == from_id,
                    RouteStation.departure_time >= input_t
                )
                .order_by(RouteStation.departure_time.asc())
                .limit(3)
                .all()
            )

            # Final combined list (before trains in ascending order)
            trains = list(reversed(before_trains)) + after_trains

        else:
            trains = trains_query.distinct().all()

        if not trains:
            raise HTTPException(404, "No trains found for selected time window")


        # ---------------- Build Result ----------------
        result = []

        for train in trains:
            # ---------------- Get from/to RouteStation ----------------
            rs_from = db.query(RouteStation).filter(RouteStation.train_id == train.train_id, RouteStation.station_id == from_id).first()
            rs_to = db.query(RouteStation).filter(RouteStation.train_id == train.train_id, RouteStation.station_id == to_id).first()
            if not rs_from or not rs_to or rs_from.stop_number >= rs_to.stop_number:
                continue

            # ---------------- Time filter ----------------
            #if time:
            #input_t = datetime.strptime(time, "%H:%M").time()
            #start_t = (datetime.combine(date.today(), input_t) - timedelta(hours=23)).time()
            #end_t = (datetime.combine(date.today(), input_t) + timedelta(hours=23)).time()
            #if not (start_t <= rs_from.departure_time <= end_t):
            #    continue

            # ---------------- Classes & Availability ----------------
            berth_query = db.query(BerthClass).filter(BerthClass.train_id == train.train_id)
            #if train_class:
            berth_query = berth_query.filter(BerthClass.class_type.ilike(f"%{train_class}%"))

            # ---------------- Classes & Availability (Show only requested class if provided) ----------------
            classes = []
            if train_class:
                # Normalize user input class type
                requested_class = normalize(train_class)

                # Map possible inputs to actual stored class names
                class_map = {
                    "1st": "1st Class",
                    "first": "1st Class",
                    "2nd": "2nd Class",
                    "second": "2nd Class",
                    "chair": "Chair Car",
                    "executive": "Executive Chair Car",
                    "exec": "Executive Chair Car"
                }

                # Find correct DB class value
                matched_class_name = next(
                    (v for k, v in class_map.items() if k in requested_class),
                    None
                )

                if not matched_class_name:
                    raise HTTPException(400, "Invalid class type requested")

                # Query only that class
                bc = (
                    db.query(BerthClass)
                    .filter(
                        BerthClass.train_id == train.train_id,
                        func.lower(BerthClass.class_type).like(func.lower(f"%{matched_class_name}%"))
                    )
                    .first()
                )

                if bc:
                    avail = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bc.berth_class_id,
                        #TrainSeatAvailability.travel_date == travel_date
                    ).first()

                    available = avail.available_seats if avail else 0
                    booked = bc.total_berths - available

                    classes.append(
                        ClassAvailability(
                            class_type=bc.class_type,
                            total_berths=bc.total_berths,
                            booked=booked,
                            available=available,
                            price=bc.price
                        )
                    )

            else:
                # No class filter → fetch all classes (existing behavior)
                for bc in db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all():
                    avail = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bc.berth_class_id,
                        #TrainSeatAvailability.travel_date == travel_date
                    ).first()

                    available = avail.available_seats if avail else 0
                    booked = bc.total_berths - available

                    classes.append(
                        ClassAvailability(
                            class_type=bc.class_type,
                            total_berths=bc.total_berths,
                            booked=booked,
                            available=available,
                            price=bc.price
                        )
                    )


            result.append(
                TrainAvailability(
                    train_id=train.train_id,
                    train_name=train.train_name,
                    train_number= str(train.train_no),
                    train_type=train.train_type,
                    from_station=polish_from,
                    to_station=polish_to,
                    travel_date=travel_date,
                    departure_time=rs_from.departure_time,
                    arrival_time=rs_to.arrival_time,
                    departure_date= travel_date,
                    classes=classes
                )
            )


        # ================= RETURN JOURNEY =================
        return_list = []

        if return_date:
            rf, rt = aliased(RouteStation), aliased(RouteStation)
            reverse_route_ids = [
                r[0] for r in db.query(rf.route_id)
                .join(rt, rf.route_id == rt.route_id)
                .filter(
                    rf.station_id == to_id,
                    rt.station_id == from_id,
                    rf.stop_number < rt.stop_number
                )
                .distinct()
                .all()
            ]

            if not reverse_route_ids:
                raise HTTPException(
                    404, f"There is no route between {polish_to} to {polish_from}"
                )

            reverse_q = db.query(Train).filter(Train.route_id.in_(reverse_route_ids))

            if return_train_number:
                rtn = int(return_train_number)
                q = reverse_q.filter(
                    (Train.train_no == rtn) | (Train.alternate_train_no == rtn)
                )
                if not q.count():
                    raise HTTPException(
                        404,
                        f"Return train number {return_train_number} is not available for the route {polish_to} to {polish_from}"
                    )
                reverse_q = q

            if return_train_name:
                q = reverse_q.filter(
                    Train.train_name.ilike(f"%{normalize(return_train_name)}%")
                )
                if not q.count():
                    raise HTTPException(404, f"Return train name '{return_train_name}' not found")
                reverse_q = q

            if return_train_type:
                q = reverse_q.filter(
                    Train.train_type.ilike(f"%{return_train_type}%")
                )
                if not q.count():
                    raise HTTPException(404, f"Return train type '{return_train_type}' not found")
                reverse_q = q

            # -------- Time filter (RETURN) --------
            if return_time:
                t = datetime.strptime(return_time, "%H:%M").time()

                before = (
                    reverse_q.join(RouteStation)
                    .filter(RouteStation.station_id == to_id, RouteStation.departure_time < t)
                    .order_by(RouteStation.departure_time.desc())
                    .limit(3)
                    .all()
                )

                after = (
                    reverse_q.join(RouteStation)
                    .filter(RouteStation.station_id == to_id, RouteStation.departure_time >= t)
                    .order_by(RouteStation.departure_time.asc())
                    .limit(3)
                    .all()
                )

                reverse_trains = list(reversed(before)) + after
            else:
                reverse_trains = reverse_q.distinct().all()

            for train in reverse_trains:
                rs_from = db.query(RouteStation).filter(
                    RouteStation.train_id == train.train_id,
                    RouteStation.station_id == to_id
                ).first()

                rs_to = db.query(RouteStation).filter(
                    RouteStation.train_id == train.train_id,
                    RouteStation.station_id == from_id
                ).first()

                if not rs_from or not rs_to or rs_from.stop_number >= rs_to.stop_number:
                    continue

                classes_rt = []
                berth_q = db.query(BerthClass).filter(BerthClass.train_id == train.train_id)

                if return_train_class:
                    berth_q = berth_q.filter(
                        func.lower(BerthClass.class_type).like(
                            f"%{normalize(return_train_class)}%"
                        )
                    )

                for bc in berth_q.all():
                    avail = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bc.berth_class_id
                    ).first()

                    available = avail.available_seats if avail else 0
                    classes_rt.append(
                        ClassAvailability(
                            class_type=bc.class_type,
                            total_berths=bc.total_berths,
                            booked=bc.total_berths - available,
                            available=available,
                            price=bc.price
                        )
                    )

                if return_train_class and not classes_rt:
                    continue

                return_list.append(
                    TrainAvailability(
                        train_id=train.train_id,
                        train_name=train.train_name,
                        train_number=str(train.train_no),
                        train_type=train.train_type,
                        from_station=polish_to,
                        to_station=polish_from,
                        travel_date=return_date,
                        departure_time=rs_from.departure_time,
                        arrival_time=rs_to.arrival_time,
                        departure_date=return_date,
                        classes=classes_rt
                    )
                )

        return {"onward": result, "return": return_list}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("search_trains failed")
        raise HTTPException(500, str(e))
