'''
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased
from sqlalchemy import and_, or_, func
from datetime import date
from models import Train, Route, Station, TrainSchedule, BerthClass, TrainSeatAvailability, Booking, Passenger, RouteStation
from fastapi import HTTPException
from schemas import (
    TrainAvailability,
    ClassAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse
)
import logging

import unicodedata

def normalize(s: str):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.combining(c)
    ).lower().strip()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- SEARCH TRAINS -------------------
def search_trains(db: Session, from_station_name: str, to_station_name: str, travel_date: date):
    try:
        # 🔹 Find stations (case-insensitive)
        from_station = None
        stations = db.query(Station).all()
        for s in stations:
            if normalize(s.station_name) == normalize(from_station_name):
                from_station = s
                break

# ✅ Normalize and match TO station
        to_station = None
        for s in stations:
            if normalize(s.station_name) == normalize(to_station_name):
                to_station = s
                break

        if not from_station or not to_station:
            logger.warning(f"Invalid stations: {from_station_name}, {to_station_name}")
            return []

        from_station_id = from_station.station_id
        to_station_id = to_station.station_id

        # 🔹 Find routes where both stations exist in correct order
        subq_from = aliased(RouteStation)
        subq_to = aliased(RouteStation)

        valid_routes = (
            db.query(subq_from.route_id)
            .join(subq_to, subq_from.route_id == subq_to.route_id)
            .filter(
                subq_from.station_id == from_station_id,
                subq_to.station_id == to_station_id,
                subq_from.stop_number < subq_to.stop_number
            )
            .distinct()
            .all()
        )

        route_ids = [r[0] for r in valid_routes]

        if not route_ids:
            logger.info(f"No route includes both {from_station_name} and {to_station_name}")
            return []

        # 🔹 Fetch trains for valid routes
        #trains = db.query(Train).filter(Train.route_id.in_(route_ids)).all()
        trains = (
            db.query(Train)
            .join(Route, Train.route_id == Route.route_id)
            .join(RouteStation, Route.route_id == RouteStation.route_id)
            .filter(RouteStation.route_id.in_(route_ids))
            .distinct()
            .all()
        )

        train_list = []

        for train in trains:
            # 🔹 Get berth classes (no date constraint)
            classes = []
            berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()

            for bclass in berth_classes:
                # Get the most recent availability record, or return 0 if none found
                availability = db.query(TrainSeatAvailability).filter(
                    TrainSeatAvailability.berth_class_id == bclass.berth_class_id
                ).order_by(TrainSeatAvailability.travel_date.desc()).first()

                available = availability.available_seats if availability else 0
                booked = bclass.total_berths - available if bclass.total_berths else 0

                classes.append(ClassAvailability(
                    class_type=bclass.class_type,
                    total_berths=bclass.total_berths,
                    booked=booked,
                    available=available,
                    price=bclass.price
                ))

            # 🔹 Get schedules for departure & arrival stations
            #schedule_from = db.query(TrainSchedule).filter(
            #    TrainSchedule.train_id == train.train_id,
            #    TrainSchedule.station_id == from_station_id
            #).first()

            #schedule_to = db.query(TrainSchedule).filter(
            #    TrainSchedule.train_id == train.train_id,
            #    TrainSchedule.station_id == to_station_id
            #).first()
    #===============================================================
        from_stop = db.query(RouteStation).filter(
            RouteStation.route_id == train.route_id,
            RouteStation.station_id == from_station_id
        ).first()

        to_stop = db.query(RouteStation).filter(
            RouteStation.route_id == train.route_id,
            RouteStation.station_id == to_station_id
        ).first()

# Fallback to schedule table only if it's stored there
        schedule_from = db.query(TrainSchedule).filter(
            TrainSchedule.train_id == train.train_id,
            TrainSchedule.station_id == from_station_id
        ).first() or from_stop

        schedule_to = db.query(TrainSchedule).filter(
            TrainSchedule.train_id == train.train_id,
            TrainSchedule.station_id == to_station_id
        ).first() or to_stop
        
            


            # 🔹 Append result (even if no availability data found)
        train_list.append(
            TrainAvailability(
                train_id=train.train_id,
                train_name=train.train_name,
                train_no=train.train_no,
                from_station=from_station.station_name,
                to_station=to_station.station_name,
                travel_date=travel_date,  # user-input reference date
                departure_time = getattr(schedule_from, "departure_time", None),
                arrival_time = getattr(schedule_to, "arrival_time", None),
                classes=classes
            )
        )    

        return train_list

    except Exception as e:
        logger.exception("Error in search_trains")
        raise HTTPException(status_code=500, detail=str(e))

'''
# ---------------------------------------------
# CRUD Operations for Train Search (Final)
# ---------------------------------------------

'''

from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from models import (
    Train, Route, Station, RouteStation,
    TrainSchedule, BerthClass, TrainSeatAvailability
)
from schemas import TrainAvailability, ClassAvailability
import unicodedata
import logging

# ---------------------------------------------
# Logger Setup
# ---------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------
# Normalize strings for station name matching
# ---------------------------------------------
def normalize(s: str):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s or "")
        if not unicodedata.combining(c)
    ).lower().strip()


# ---------------------------------------------
# Main Search Function
# ---------------------------------------------
def search_trains(
    db: Session,
    from_station_name: str,
    to_station_name: str,
    travel_date: date,
    train_name: str | None = None,
    train_number: str | None = None,
    train_class: str | None = None,
    time: str | None = None
):
    try:
        logger.info(
            "search_trains called with: from=%s to=%s date=%s name=%s number=%s class=%s time=%s",
            from_station_name, to_station_name, travel_date,
            train_name, train_number, train_class, time
        )

        # -------------------------------------------------
        # 1️⃣ Resolve From & To Stations (normalized match)
        # -------------------------------------------------
        stations = db.query(Station).all()
        from_station = next((s for s in stations if normalize(s.station_name) == normalize(from_station_name)), None)
        to_station = next((s for s in stations if normalize(s.station_name) == normalize(to_station_name)), None)

        if not from_station or not to_station:
            raise HTTPException(404, "Station not found")

        from_station_id = from_station.station_id
        to_station_id = to_station.station_id

        # -------------------------------------------------
        # 2️⃣ Early Train Number Filter (strict, integer)
        # -------------------------------------------------
        specific_train = None
        if train_number:
            try:
                tn = int(train_number)
            except ValueError:
                raise HTTPException(400, "Train number must be numeric")

            specific_train = db.query(Train).filter(Train.train_no == tn).first()

            if specific_train:
                # Ensure this train follows the route order
                rs1 = db.query(RouteStation).filter(
                    RouteStation.route_id == specific_train.route_id,
                    RouteStation.station_id == from_station_id
                ).first()

                rs2 = db.query(RouteStation).filter(
                    RouteStation.route_id == specific_train.route_id,
                    RouteStation.station_id == to_station_id
                ).first()

                if not (rs1 and rs2 and rs1.stop_number < rs2.stop_number):
                    return []  # Train exists but does not travel between these stations

        # -------------------------------------------------
        # 3️⃣ Find Valid Route IDs containing both stations
        # -------------------------------------------------
        rf = aliased(RouteStation)
        rt = aliased(RouteStation)

        routes = (
            db.query(rf.route_id)
            .join(rt, rf.route_id == rt.route_id)
            .filter(
                rf.station_id == from_station_id,
                rt.station_id == to_station_id,
                rf.stop_number < rt.stop_number
            )
            .distinct()
            .all()
        )

        route_ids = [r[0] for r in routes]
        if not route_ids:
            raise HTTPException(404, "No route contains both stations in correct order")

        # -------------------------------------------------
        # 4️⃣ Base Query: All trains for these route(s)
        # -------------------------------------------------
        rs_from = aliased(RouteStation)
        rs_to = aliased(RouteStation)

        query = (
            db.query(Train)
            .join(rs_from, rs_from.route_id == Train.route_id)
            .join(rs_to, rs_to.route_id == Train.route_id)
            .filter(
                rs_from.station_id == from_station_id,
                rs_to.station_id == to_station_id,
                rs_from.stop_number < rs_to.stop_number,
                Train.route_id.in_(route_ids)
            )
        )

        # -------------------------------------------------
        # 5️⃣ Apply Additional Filters
        # -------------------------------------------------

        # Train number filter → after validating route
        if specific_train:
            query = query.filter(Train.train_id == specific_train.train_id)

        # Train name filter (partial)
        if train_name:
            query = query.filter(Train.train_name.ilike(f"%{train_name}%"))

        # Class filter
        if train_class:
            query = query.join(BerthClass).filter(
                BerthClass.class_type.ilike(f"%{train_class}%")
            )

        # Time filter → 1 hour window from departure
        if time:
            input_t = datetime.strptime(time, "%H:%M").time()
            start_t = input_t
            end_t = (datetime.combine(date.today(), input_t) + timedelta(hours=1)).time()

            query = (
                query.join(TrainSchedule)
                .filter(
                    TrainSchedule.station_id == from_station_id,
                    TrainSchedule.departure_time >= start_t,
                    TrainSchedule.departure_time <= end_t
                )
            )

        # Ensure unique trains
        trains = query.distinct().all()

        if not trains:
            raise HTTPException(404, "No matching trains found")

        # -------------------------------------------------
        # 6️⃣ Build the Response (train + classes + schedule)
        # -------------------------------------------------
        result = []

        for train in trains:
            # Fetch berth classes
            berth_classes = db.query(BerthClass).filter(
                BerthClass.train_id == train.train_id
            ).all()

            class_list = []
            for bc in berth_classes:
                avail = db.query(TrainSeatAvailability).filter(
                    TrainSeatAvailability.berth_class_id == bc.berth_class_id
                ).order_by(TrainSeatAvailability.travel_date.desc()).first()

                available = avail.available_seats if avail else 0
                booked = bc.total_berths - available

                class_list.append(
                    ClassAvailability(
                        class_type=bc.class_type,
                        total_berths=bc.total_berths,
                        booked=booked,
                        available=available,
                        price=bc.price
                    )
                )

            # Fetch schedule details
            schedule_from = db.query(TrainSchedule).filter(
                TrainSchedule.train_id == train.train_id,
                TrainSchedule.station_id == from_station_id
            ).first()

            schedule_to = db.query(TrainSchedule).filter(
                TrainSchedule.train_id == train.train_id,
                TrainSchedule.station_id == to_station_id
            ).first()

            # Add train entry
            result.append(
                TrainAvailability(
                    train_id=train.train_id,
                    train_name=train.train_name,
                    train_no=train.train_no,
                    from_station=from_station.station_name,
                    to_station=to_station.station_name,
                    travel_date=travel_date,
                    departure_time=schedule_from.departure_time if schedule_from else None,
                    arrival_time=schedule_to.arrival_time if schedule_to else None,
                    classes=class_list
                )
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in search_trains")
        raise HTTPException(500, str(e))


'''

'''
# ---------------------------------------------
# CRUD Operations for Train Search (Final)
# ---------------------------------------------

from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from models import (
    Train, Route, Station, RouteStation,
    TrainSchedule, BerthClass, TrainSeatAvailability
)
from schemas import TrainAvailability, ClassAvailability, RoundTripResponse
import unicodedata
import logging

# ---------------------------------------------
# Logger Setup
# ---------------------------------------------
#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)
# ✅ Logger Setup that forces console output even in worker threads
logger = logging.getLogger("train_search")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
console_handler.setFormatter(formatter)

logger.handlers.clear()  # ✅ Remove existing handlers if any
logger.addHandler(console_handler)  # ✅ Force add console handler



# ---------------------------------------------
# Normalize strings for station name matching
# ---------------------------------------------
def normalize(s: str):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s or "")
        if not unicodedata.combining(c)
    ).lower().strip()


# ---------------------------------------------
# Main Search Function
# ---------------------------------------------
def search_trains(
    db: Session,
    from_station_name: str,
    to_station_name: str,
    travel_date: date,
    return_date: date | None = None,
    train_name: str | None = None,
    train_number: str | None = None,
    train_type: str | None = None,
    train_class: str | None = None,
    time: str | None = None
):
    try:
        # ---------------- Normalize Stations ----------------
        stations = db.query(Station).all()
        from_station = next((s for s in stations if normalize(s.station_name) == normalize(from_station_name)), None)
        to_station = next((s for s in stations if normalize(s.station_name) == normalize(to_station_name)), None)

        if not from_station or not to_station:
            raise HTTPException(404, "Station not found")

        from_station_id = from_station.station_id
        to_station_id = to_station.station_id

        # ---------------- Validate Route Order ----------------
        rf = aliased(RouteStation)
        rt = aliased(RouteStation)
        routes = (
            db.query(rf.route_id)
            .join(rt, rf.route_id == rt.route_id)
            .filter(
                rf.station_id == from_station_id,
                rt.station_id == to_station_id,
                rf.stop_number < rt.stop_number
            ).distinct().all()
        )

        route_ids = [r[0] for r in routes]
        if not route_ids:
            raise HTTPException(404, "No route contains both stations in correct order")



        specific_train = None
        if train_number:
            try:
                tn = int(train_number)
            except ValueError:
                raise HTTPException(400, "Train number must be numeric")

            specific_train = db.query(Train).filter(Train.train_no == tn).first()

            if not specific_train:
                raise HTTPException(404, "Train not found")

            if specific_train.route_id not in route_ids:
                raise HTTPException(
                    404,
                    f"Train {train_number} does not run between {from_station_name} → {to_station_name} on the selected date"
                )


        

        # ---------------- Base Query (Train Search) ----------------
        rs_from = aliased(RouteStation)
        rs_to = aliased(RouteStation)
        query = (
            db.query(Train)
            .join(rs_from, rs_from.route_id == Train.route_id)
            .join(rs_to, rs_to.route_id == Train.route_id)
            .filter(
                rs_from.station_id == from_station_id,
                rs_to.station_id == to_station_id,
                rs_from.stop_number < rs_to.stop_number,
                Train.route_id.in_(route_ids)
            )
        )

        if specific_train:
            query = query.filter(Train.train_no == int(train_number))

        if train_name:
            query = query.filter(Train.train_name.ilike(f"%{train_name}%"))

        if train_type:
            query = query.filter(Train.train_type.ilike(f"%{train_type}%"))

        if train_class:
            query = query.join(BerthClass).filter(BerthClass.class_type.ilike(f"%{train_class}%"))

        if time:
            try:
                input_t = datetime.strptime(time, "%H:%M").time()
                now = datetime.combine(date.today(), input_t)
                start_t = (now - timedelta(hours=1)).time()
                end_t = (now + timedelta(hours=1)).time()
                
                logger.info(f"⏰ Time buffer window: {start_t} → {end_t}")

                # ✅ Reset joins for clean schedule filter path
                query = query.join(RouteStation, RouteStation.train_id == Train.train_id).filter(
                    RouteStation.station_id == from_station_id,
                    RouteStation.departure_time.between(start_t, end_t)
                )

                logger.info("🔎 SQL After Time Filter:")
                logger.info(str(query.statement.compile(compile_kwargs={"literal_binds": True})))

            except ValueError:
                logger.error("❌ Invalid time format")
                raise HTTPException(400, "Time must be in HH:MM format")




        trains = query.distinct().all()
        if not trains:
            raise HTTPException(404, "No matching trains found")

        # ---------------- Build Response ----------------
        result = []
        for train in trains:
            berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()
            class_list = []
            for bc in berth_classes:
                avail = db.query(TrainSeatAvailability).filter(
                    TrainSeatAvailability.berth_class_id == bc.berth_class_id,
                    TrainSeatAvailability.travel_date == travel_date
                ).first()

                available = avail.available_seats if avail else 0
                booked = bc.total_berths - available

                class_list.append(
                    ClassAvailability(
                        class_type=bc.class_type,
                        total_berths=bc.total_berths,
                        booked=booked,
                        available=available,
                        price=bc.price
                    )
                )

            schedule_from = db.query(TrainSchedule).filter(
                TrainSchedule.train_id == train.train_id,
                TrainSchedule.station_id == from_station_id
            ).first()

            schedule_to = db.query(TrainSchedule).filter(
                TrainSchedule.train_id == train.train_id,
                TrainSchedule.station_id == to_station_id
            ).first()

            result.append(
                TrainAvailability(
                    train_id=train.train_id,
                    train_name=train.train_name,
                    train_no=train.train_no,
                    from_station=from_station.station_name,
                    to_station=to_station.station_name,
                    travel_date=travel_date,
                    train_type=train.train_type if train_type is None else train_type,
                    departure_time=RouteStation.departure_time if RouteStation else None,
                    arrival_time=RouteStation.arrival_time if RouteStation else None,
                    classes=class_list
                )
            )

        # ---------------- Handle Return Trip ----------------
        return_list = []
        if return_date:
            return_list = search_trains(
                db,
                to_station_name,
                from_station_name,
                return_date,
                None,
                train_name,
                train_number,
                train_type,
                train_class,
                time
            )["onward"]

        # ---------------- Final Correct Response ----------------
        return {
            "onward": result,
            "return": return_list
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in search_trains")
        raise HTTPException(500, str(e))

'''
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
    return_date: date | None = None,
    train_name: str | None = None,
    train_number: str | None = None,
    train_type: str | None = None,
    train_class: str | None = None,
    time: str | None = None
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
        if train_number:
            try:
                trains_query = trains_query.filter(Train.train_no == int(train_number))
            except ValueError:
                raise HTTPException(400, "Train number must be numeric")
        if train_name:
            trains_query = trains_query.filter(Train.train_name.ilike(f"%{train_name}%"))
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
            if time:
                input_t = datetime.strptime(time, "%H:%M").time()
                start_t = (datetime.combine(date.today(), input_t) - timedelta(hours=1)).time()
                end_t = (datetime.combine(date.today(), input_t) + timedelta(hours=1)).time()
                if not (start_t <= rs_from.departure_time <= end_t):
                    continue

            # ---------------- Classes & Availability ----------------
            berth_query = db.query(BerthClass).filter(BerthClass.train_id == train.train_id)
            if train_class:
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
                        TrainSeatAvailability.travel_date == travel_date
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
                        TrainSeatAvailability.travel_date == travel_date
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

                # Classes availability for return date
                classes_rt = []
                # ✅ add class filter ONLY (train filters must be ignored for return)
                reverse_berth_query = db.query(BerthClass).filter(BerthClass.train_id == train.train_id)

                if train_class:
                    reverse_berth_query = reverse_berth_query.filter(
                        BerthClass.class_type.ilike(f"%{train_class}%")
                    )

                for bc in reverse_berth_query.all():
                    avail_rt = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bc.berth_class_id,
                        TrainSeatAvailability.travel_date == return_date
                    ).first()

                    available_rt = avail_rt.available_seats if avail_rt else 0
                    booked_rt = bc.total_berths - available_rt

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
