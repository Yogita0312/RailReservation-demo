from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_
from sqlalchemy import func
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from models import Train, RouteStation, Station, BerthClass, TrainSeatAvailability
from schemas import TrainAvailability, ClassAvailability
import unicodedata
import logging

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


# ---------------- Main search function ----------------
def search_trains(
    db: Session,
    from_station_name: str,
    to_station_name: str,
    travel_date: date,
    train_class: str, 
    time: str,
    return_date: date | None = None,
    return_time: str | None = None,
    train_name: str | None = None,
    train_number: str | None = None,
    train_type: str | None = None
    
):
    try:
        logger.info("🔥 search_trains called")
        logger.info(f"params: from={from_station_name} to={to_station_name} date={travel_date} time={time} train_number={train_number}")

        # ---------------- Get Stations ----------------
        stations = db.query(Station).all()

# Match by English OR Polish OR station code
        from_station = next(
            (s for s in stations if normalize(s.station_name) == normalize(from_station_name)
            or normalize(s.station_name_PL) == normalize(from_station_name)
            or normalize(s.station_id_code) == normalize(from_station_name)),
            None)

        to_station = next(
            (s for s in stations if normalize(s.station_name) == normalize(to_station_name)
            or normalize(s.station_name_PL) == normalize(to_station_name)
            or normalize(s.station_id_code) == normalize(to_station_name)),
            None)

        if not from_station or not to_station:
            raise HTTPException(404, "Station not found")

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
            raise HTTPException(404, "No route contains both stations in correct order")

        # ---------------- Base Train Query ----------------
        trains_query = db.query(Train).filter(Train.route_id.in_(route_ids))
        #if train_number:                    <==(commented this part so that api will not filter on basis on train name and no. Uncomment when required filtering)
        #    try:
        #        trains_query = trains_query.filter(Train.train_no == int(train_number))
        #    except ValueError:
        #        raise HTTPException(400, "Train number must be numeric")
        #if train_name:
        #    trains_query = trains_query.filter(Train.train_name.ilike(f"%{train_name}%"))
        if train_type:
            trains_query = trains_query.filter(Train.train_type.ilike(f"%{train_type}%"))

        trains = trains_query.distinct().all()
        if not trains:
            logger.info("No matching trains found after applying filters")
            raise HTTPException(404, "No matching trains found")

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

        # ---------------- Handle Return Trip ----------------
        # ---------------- Handle Return Trip (No Filters Applied) ----------------
        return_list = []
        if return_date:
            # Fetch all trains for reverse direction WITHOUT any filters
            reverse_routes = (
                db.query(RouteStation.route_id)
                .filter(
                    RouteStation.station_id.in_([from_id, to_id])
                )
                .distinct()
                .all()
            )
            reverse_route_ids = [r[0] for r in reverse_routes]

            reverse_trains_query = db.query(Train).filter(Train.route_id.in_(reverse_route_ids))
            all_reverse_trains = reverse_trains_query.distinct().all()

            # Build return result with Polish station names
            for train in all_reverse_trains:
                rs_from_rt = db.query(RouteStation).filter(RouteStation.train_id == train.train_id, RouteStation.station_id == to_id).first()
                rs_to_rt = db.query(RouteStation).filter(RouteStation.train_id == train.train_id, RouteStation.station_id == from_id).first()

                if not rs_from_rt or not rs_to_rt or rs_from_rt.stop_number >= rs_to_rt.stop_number:
                    continue

                #if return_time:
                #    input_rt = datetime.strptime(return_time, "%H:%M").time()
                #    start_rt = (datetime.combine(date.today(), input_rt) - timedelta(hours=1)).time()
                #    end_rt = (datetime.combine(date.today(), input_rt) + timedelta(hours=1)).time()

                #    if not (start_rt <= rs_from_rt.departure_time <= end_rt):
                #        continue    

                # Classes availability for return date
                classes_rt = []
                # ✅ add class filter ONLY (train filters must be ignored for return)
                reverse_berth_query = db.query(BerthClass).filter(BerthClass.train_id == train.train_id)

                #if train_class:
                reverse_berth_query = reverse_berth_query.filter(
                        BerthClass.class_type.ilike(f"%{train_class}%")
                    )

                for bc in reverse_berth_query.all():
                    avail_rt = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bc.berth_class_id,
                        #TrainSeatAvailability.travel_date == return_date
                    ).first()

                    available_rt = avail_rt.available_seats if avail_rt else 0
                    booked_rt = bc.total_berths - available_rt
                    logger.info(f"🔎 Return Availability Check → TrainID={bc.train_id}, Class={bc.class_type}, Available Seats={avail_rt}")

                    classes_rt.append(
                        ClassAvailability(
                            class_type=bc.class_type,
                            total_berths=bc.total_berths,
                            booked=booked_rt,
                            available=available_rt,  # fixed earlier ✅ keep this
                            price=bc.price
                        )
                    )


                return_list.append(
                    TrainAvailability(
                        train_id=train.train_id,
                        train_name=train.train_name,
                        train_number=str(train.train_no),
                        train_type=train.train_type,
                        from_station=polish_to,   # ✅ always Polish
                        to_station=polish_from,   # ✅ always Polish
                        travel_date=return_date,
                        departure_time=rs_from_rt.departure_time,
                        arrival_time=rs_to_rt.arrival_time,
                        departure_date=return_date,
                        classes=classes_rt
                    )
                )


        return {"onward": result, "return": return_list}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in search_trains")
        raise HTTPException(500, str(e))
