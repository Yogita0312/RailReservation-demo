'''
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from models import Train, Route, Station, TrainSchedule, BerthClass, TrainSeatAvailability, Booking, Passenger
from schemas import (
    TrainAvailability,
    ClassAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse
)
import logging

# Setup logging to see errors in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- SEARCH TRAINS -------------------
def search_trains(db: Session, from_station_name: str, to_station_name: str, travel_date: date):
    try:
        # Get station IDs
        from_station = db.query(Station).filter(Station.station_name == from_station_name).first()
        to_station = db.query(Station).filter(Station.station_name == to_station_name).first()

        if not from_station or not to_station:
            logger.info(f"No station found: {from_station_name} or {to_station_name}")
            return []

        from_station_id = from_station.station_id
        to_station_id = to_station.station_id

        # Find routes matching source -> destination
        routes = db.query(Route).filter(
            and_(
                Route.source_station_id == from_station_id,
                Route.destination_station_id == to_station_id
            )
        ).all()

        if not routes:
            logger.info(f"No routes found between {from_station_name} and {to_station_name}")
            return []

        # Gather trains per route
        train_list = []
        for route in routes:
            trains = db.query(Train).filter(Train.route_id == route.route_id).all()
            for train in trains:
                # Get berth classes and availability
                classes = []
                berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()
                for bclass in berth_classes:
                    availability = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bclass.berth_class_id
                    ).first()
                    available_seats = availability.available_seats if availability else 0

                    classes.append(ClassAvailability(
                        class_name=bclass.class_name,
                        available_seats=available_seats
                    ))

                train_list.append(TrainAvailability(
                    train_id=train.train_id,
                    train_name=train.train_name,
                    from_station=from_station_name,
                    to_station=to_station_name,
                    travel_date=travel_date,
                    classes=classes
                ))

        return train_list

    except Exception as e:
        logger.exception("Error in search_trains")
        return []


# ------------------- BOOK TICKET -------------------
def book_ticket(db: Session, booking: BookingRequest):
    try:
        # Validate stations
        from_station = db.query(Station).filter(Station.station_name == booking.from_station).first()
        to_station = db.query(Station).filter(Station.station_name == booking.to_station).first()

        if not from_station or not to_station:
            return BookingFailureResponse(message="Invalid station names provided.")

        # Validate train and class
        train = db.query(Train).filter(Train.train_id == booking.train_id).first()
        bclass = db.query(BerthClass).filter(
            and_(
                BerthClass.train_id == booking.train_id,
                BerthClass.class_name == booking.berth_class
            )
        ).first()

        if not train or not bclass:
            return BookingFailureResponse(message="Invalid train or berth class.")

        # Check seat availability
        availability = db.query(TrainSeatAvailability).filter(
            TrainSeatAvailability.berth_class_id == bclass.berth_class_id
        ).first()

        if not availability or availability.available_seats < booking.num_seats:
            return BookingFailureResponse(message="Not enough seats available.")

        # Deduct seats
        availability.available_seats -= booking.num_seats
        db.add(availability)

        # Create booking record
        new_booking = Booking(
            passenger_id=booking.passenger_id,
            train_id=booking.train_id,
            berth_class_id=bclass.berth_class_id,
            journey_date=booking.travel_date,
            seat_number=booking.seat_number
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return BookingSuccessResponse(
            booking_id=new_booking.booking_id,
            message="Booking successful."
        )

    except Exception as e:
        logger.exception("Error in book_ticket")
        return BookingFailureResponse(message="Internal server error during booking.")
'''

'''
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from models import Train, Route, Station, TrainSchedule, BerthClass, TrainSeatAvailability, Booking, Passenger
from schemas import BookingRequest, BookingSuccessResponse, BookingFailureResponse, TrainAvailability, ClassAvailability

def search_trains(db: Session, from_station_name: str, to_station_name: str, travel_date: date):
    # Get station IDs from names
    from_station = db.query(Station).filter(Station.station_name == from_station_name).first()
    to_station = db.query(Station).filter(Station.station_name == to_station_name).first()

    if not from_station or not to_station:
        return []  # No station found

    from_station_id = from_station.station_id
    to_station_id = to_station.station_id

    # Find routes containing both stations (from before to)
    routes = db.query(Route).filter(
        and_(
            Route.from_station_id == from_station_id,
            Route.to_station_id == to_station_id
        )
    ).all()

    train_list = []
    for route in routes:
        train = db.query(Train).filter(Train.train_id == route.train_id).first()
        schedule = db.query(TrainSchedule).filter(
            and_(
                TrainSchedule.train_id == train.train_id,
                TrainSchedule.travel_date == travel_date
            )
        ).first()

        if not schedule:
            continue

        # Check seat availability for each class
        classes = []
        berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()
        for bclass in berth_classes:
            availability = db.query(TrainSeatAvailability).filter(
                and_(
                    TrainSeatAvailability.train_id == train.train_id,
                    TrainSeatAvailability.class_id == bclass.class_id,
                    TrainSeatAvailability.travel_date == travel_date
                )
            ).first()

            available_seats = availability.available_seats if availability else 0

            classes.append(ClassAvailability(
                class_name=bclass.class_name,
                available_seats=available_seats
            ))

        train_list.append(TrainAvailability(
            train_id=train.train_id,
            train_name=train.train_name,
            from_station=from_station_name,
            to_station=to_station_name,
            travel_date=travel_date,
            classes=classes
        ))

    return train_list


def book_ticket(db: Session, booking: BookingRequest):
    # Validate stations
    from_station = db.query(Station).filter(Station.station_name == booking.from_station).first()
    to_station = db.query(Station).filter(Station.station_name == booking.to_station).first()

    if not from_station or not to_station:
        return BookingFailureResponse(message="Invalid station names provided.")

    # Validate train and class
    train = db.query(Train).filter(Train.train_id == booking.train_id).first()
    bclass = db.query(BerthClass).filter(
        and_(
            BerthClass.train_id == booking.train_id,
            BerthClass.class_name == booking.berth_class
        )
    ).first()

    if not train or not bclass:
        return BookingFailureResponse(message="Invalid train or berth class.")

    # Check seat availability
    availability = db.query(TrainSeatAvailability).filter(
        and_(
            TrainSeatAvailability.train_id == booking.train_id,
            TrainSeatAvailability.class_id == bclass.class_id,
            TrainSeatAvailability.travel_date == booking.travel_date
        )
    ).first()

    if not availability or availability.available_seats < booking.num_seats:
        return BookingFailureResponse(message="Not enough seats available.")

    # Deduct seats
    availability.available_seats -= booking.num_seats
    db.add(availability)

    # Create booking record
    new_booking = Booking(
        train_id=booking.train_id,
        from_station_id=from_station.station_id,
        to_station_id=to_station.station_id,
        travel_date=booking.travel_date,
        class_id=bclass.class_id,
        num_seats=booking.num_seats
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return BookingSuccessResponse(
        booking_id=new_booking.booking_id,
        message="Booking successful."
    )
'''


'''
from sqlalchemy.orm import Session
from sqlalchemy import and_, asc
from datetime import date, datetime
from models import Train, RouteStation, Station, TrainSchedule, BerthClass, TrainSeatAvailability, Booking, Passenger
from schemas import TrainAvailability, ClassAvailability, BookingRequest, BookingSuccessResponse, BookingFailureResponse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- SEARCH TRAINS -------------------
def search_trains(db: Session, from_station_name: str, to_station_name: str, travel_date: date):
    try:
        # Match stations (case-insensitive)
        from_station = db.query(Station).filter(Station.station_name.ilike(from_station_name)).first()
        to_station = db.query(Station).filter(Station.station_name.ilike(to_station_name)).first()

        if not from_station or not to_station:
            logger.info(f"No station found: {from_station_name} or {to_station_name}")
            return []

        # Find all trains that have both stations in route_stations
        trains = db.query(Train).join(RouteStation).filter(
            RouteStation.station_id.in_([from_station.station_id, to_station.station_id])
        ).all()

        result = []

        for train in trains:
            # Get stop numbers for from and to
            rs_from = db.query(RouteStation).filter(
                RouteStation.train_id == train.train_id,
                RouteStation.station_id == from_station.station_id
            ).first()

            rs_to = db.query(RouteStation).filter(
                RouteStation.train_id == train.train_id,
                RouteStation.station_id == to_station.station_id
            ).first()

            # Only consider trains where from comes before to
            if not rs_from or not rs_to or rs_from.stop_number >= rs_to.stop_number:
                continue

            # Check schedule (assuming daily trains; adjust if you store running_days)
            schedule = db.query(TrainSchedule).filter(TrainSchedule.train_id == train.train_id).first()
            if not schedule:
                continue

            # Get berth classes and availability
            classes = []
            berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()
            for bclass in berth_classes:
                availability = db.query(TrainSeatAvailability).filter(
                    TrainSeatAvailability.berth_class_id == bclass.berth_class_id
                ).first()
                available_seats = availability.available_seats if availability else 0

                classes.append(ClassAvailability(
                    class_name=bclass.class_name,
                    available_seats=available_seats
                ))

            result.append(TrainAvailability(
                train_id=train.train_id,
                train_name=train.train_name,
                from_station=from_station.station_name,
                to_station=to_station.station_name,
                travel_date=travel_date,
                classes=classes
            ))

        return result

    except Exception as e:
        logger.exception("Error in search_trains")
        return []

# ------------------- BOOK TICKET -------------------
def book_ticket(db: Session, booking: BookingRequest):
    try:
        # Validate stations
        from_station = db.query(Station).filter(Station.station_name.ilike(booking.from_station)).first()
        to_station = db.query(Station).filter(Station.station_name.ilike(booking.to_station)).first()

        if not from_station or not to_station:
            return BookingFailureResponse(message="Invalid station names provided.")

        # Validate train and class
        train = db.query(Train).filter(Train.train_id == booking.train_id).first()
        bclass = db.query(BerthClass).filter(
            and_(
                BerthClass.train_id == booking.train_id,
                BerthClass.class_name == booking.berth_class
            )
        ).first()

        if not train or not bclass:
            return BookingFailureResponse(message="Invalid train or berth class.")

        # Check seat availability
        availability = db.query(TrainSeatAvailability).filter(
            TrainSeatAvailability.berth_class_id == bclass.berth_class_id
        ).first()

        if not availability or availability.available_seats < booking.num_seats:
            return BookingFailureResponse(message="Not enough seats available.")

        # Deduct seats
        availability.available_seats -= booking.num_seats
        db.add(availability)

        # Create booking record
        new_booking = Booking(
            passenger_id=booking.passenger_id,
            train_id=booking.train_id,
            berth_class_id=bclass.berth_class_id,
            journey_date=booking.travel_date,
            seat_number=booking.seat_number
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return BookingSuccessResponse(
            booking_id=new_booking.booking_id,
            message="Booking successful."
        )

    except Exception as e:
        logger.exception("Error in book_ticket")
        return BookingFailureResponse(message="Internal server error during booking.")
'''



from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date
from models import Train, Route, Station, TrainSchedule, BerthClass, TrainSeatAvailability, Booking, Passenger
from fastapi import HTTPException
from schemas import (
    TrainAvailability,
    ClassAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse
)
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- SEARCH TRAINS -------------------
def search_trains(db: Session, from_station_name: str, to_station_name: str, travel_date: date):
    try:
        # Case-insensitive and trimmed station lookup
        from_station = db.query(Station).filter(
            func.lower(func.trim(Station.station_name)) == from_station_name.lower().strip()
        ).first()

        to_station = db.query(Station).filter(
            func.lower(func.trim(Station.station_name)) == to_station_name.lower().strip()
        ).first()

        #if not from_station or not to_station:
        #    logger.info(f"No station found: {from_station_name} or {to_station_name}")
        #    return []
        if from_station:
            print(f"[DEBUG] From station '{from_station_name}' ID: {from_station.station_id}")
            logger.info(f"From station '{from_station_name}' ID: {from_station.station_id}")
        else:
            print(f"[DEBUG] From station '{from_station_name}' not found!")


        if to_station:
             print(f"To station '{to_station_name}' found with ID: {to_station.station_id}")
        else:
             logger.warning(f"To station '{to_station_name}' not found!")

        from_station_id = from_station.station_id
        to_station_id = to_station.station_id

        # Find routes matching source -> destination
        routes = db.query(Route).filter(
            and_(
                Route.source_station_id == from_station_id,
                Route.destination_station_id == to_station_id
            )
        ).all()

        if not routes:
            logger.info(f"No routes found between {from_station_name} and {to_station_name}")
            return []

        # Gather trains per route
        train_list = []
        for route in routes:
            trains = db.query(Train).filter(Train.route_id == route.route_id).all()
            for train in trains:
                # Get berth classes and availability
                classes = []
                berth_classes = db.query(BerthClass).filter(BerthClass.train_id == train.train_id).all()
                for bclass in berth_classes:
                    availability = db.query(TrainSeatAvailability).filter(
                        TrainSeatAvailability.berth_class_id == bclass.berth_class_id
                    ).first()

                    classes.append(ClassAvailability(
                        class_type=bclass.class_type,
                        total_berths=bclass.total_berths,
                        booked=bclass.total_berths - (availability.available_seats if availability else 0),
                        available=availability.available_seats if availability else 0,
                        price=bclass.price
                    ))

                # Fetch schedule for this train, route, and from_station
                schedule = db.query(TrainSchedule).filter(
                    TrainSchedule.train_id == train.train_id,
                    TrainSchedule.route_id == route.route_id,
                    TrainSchedule.station_id == from_station_id
                ).first()

                departure_time = schedule.departure_time if schedule else None
                arrival_time = schedule.arrival_time if schedule else None

                train_list.append(TrainAvailability(
                    train_id=train.train_id,
                    train_name=train.train_name,
                    train_no=train.train_no,
                    from_station=from_station_name,
                    to_station=to_station_name,
                    travel_date=travel_date,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    classes=classes
                ))

        return train_list

    except Exception as e:
        logger.exception("Error in search_trains")
        return []


'''
# ------------------- BOOK TICKET -------------------
def book_ticket(db: Session, booking: BookingRequest):
    try:
        # 1. Fetch train
        train = db.query(Train).filter(Train.train_name == booking.train_name).first()
        if not train:
            raise HTTPException(status_code=404, detail="Train not found")

        # 2. Fetch berth class for this train (with price)
        berth_class = db.query(BerthClass).filter(
            BerthClass.train_id == train.train_id,
            BerthClass.class_type == booking.travel_class
        ).first()
        if not berth_class:
            raise HTTPException(status_code=404, detail="Invalid travel class for this train")

        # ✅ Fetch ticket price from berth_class table
        ticket_price = berth_class.price
        total_price = ticket_price * len(booking.passengers)

        # 3. Check seat availability
        seat_availability = db.query(TrainSeatAvailability).filter(
            TrainSeatAvailability.train_id == train.train_id,
            TrainSeatAvailability.berth_class_id == berth_class.berth_class_id,
            TrainSeatAvailability.travel_date == booking.travel_date
        ).with_for_update().first()

        if not seat_availability:
            raise HTTPException(status_code=404, detail="No seat availability for this date/class")

        if seat_availability.available_seats < len(booking.passengers):
            raise HTTPException(status_code=400, detail="Not enough seats available")

        # Deduct seats
        seat_availability.available_seats -= len(booking.passengers)

        # 4. Add passengers first
        passenger_ids = []
        for p in booking.passengers:
            passenger = Passenger(
                name=p.name,
                gender=p.gender,
                age=p.age
            )
            db.add(passenger)
            db.flush()  # ensures passenger_id is generated
            passenger_ids.append(passenger.passenger_id)

        if not passenger_ids:
            raise HTTPException(status_code=400, detail="No passengers provided")

        primary_passenger_id = passenger_ids[0]  # link booking with first passenger

        # 5. Create booking linked to primary passenger
        new_booking = Booking(
            passenger_id=primary_passenger_id,
            train_id=train.train_id,
            berth_class_id=berth_class.berth_class_id,
            travel_date=booking.travel_date,
            ticket_count=len(booking.passengers),
            status="CONFIRMED"
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        # ✅ Return proper response model
        return BookingSuccessResponse(
            status="CONFIRMED",
            train_name=train.train_name,
            train_no=train.train_no,
            travel_date=booking.travel_date,
            class_type=booking.travel_class,
            ticket_price=ticket_price,
            passengers=len(booking.passengers),
            total_price=total_price
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error booking ticket: {str(e)}")
'''