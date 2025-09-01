'''
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Date, Time, Text
from database import Base

class Station(Base):
    __tablename__ = "stations"
    station_id = Column(Integer, primary_key=True, index=True)
    station_name = Column(String(100), unique=True, nullable=False)
    platform_count = Column(Integer)

class Train(Base):
    __tablename__ = "trains"
    train_id = Column(Integer, primary_key=True, index=True)
    train_no = Column(Integer, unique=True, nullable=False)
    train_name = Column(String(100), nullable=False)
    seating_type = Column(String(50))

class Route(Base):
    __tablename__ = "routes"
    route_id = Column(Integer, primary_key=True, index=True)
    source_station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"), nullable=False)
    destination_station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"), nullable=False)
\
class BerthClass(Base):
    __tablename__ = "berth_classes"
    berth_class_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    class_type = Column(String(50))
    total_berths = Column(Integer)
    price = Column(Numeric(10,2))

class RouteStation(Base):
    __tablename__ = "route_stations"
    route_station_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    station_id = Column(Integer, ForeignKey("stations.station_id"))
    stop_number = Column(Integer)
    arrival_time = Column(Time)
    departure_time = Column(Time)
    distance_from_start_km = Column(Integer)

class Passenger(Base):
    __tablename__ = "passengers"
    passenger_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    contact_info = Column(String(100))

class Booking(Base):
    __tablename__ = "bookings"
    booking_id = Column(Integer, primary_key=True, index=True)
    passenger_id = Column(Integer, ForeignKey("passengers.passenger_id", ondelete="CASCADE"))
    train_id = Column(Integer, ForeignKey("trains.train_id"))
    from_station_id = Column(Integer, ForeignKey("stations.station_id"))
    to_station_id = Column(Integer, ForeignKey("stations.station_id"))
    class_type = Column(String(50))
    ticket_count = Column(Integer, default=1)
    status = Column(String(20))
    travel_date = Column(Date)
    seat_no = Column(String(10))
    ticket_price = Column(Numeric(10,2))

class TrainSeatAvailability(Base):
    __tablename__ = "train_seat_availability"
    availability_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id"))
    class_type = Column(String(50))
    travel_date = Column(Date)
    total_seats = Column(Integer)
    booked_seats = Column(Integer)

class SeatMapping(Base):
    __tablename__ = "seat_mappings"
    mapping_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id"))
    station_id = Column(Integer, ForeignKey("stations.station_id"))
    class_type = Column(String(50))
    booked_seats = Column(Text)
    travel_date = Column(Date)
'''

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from database import Base


# ------------------- Stations -------------------
class Station(Base):
    __tablename__ = "stations"
    station_id = Column(Integer, primary_key=True, index=True)
    station_name = Column(String(100), unique=True, nullable=False)

    # relationships
    source_routes = relationship("Route", back_populates="source_station",
                                 foreign_keys="Route.source_station_id")
    destination_routes = relationship("Route", back_populates="destination_station",
                                      foreign_keys="Route.destination_station_id")
    route_stations = relationship("RouteStation", back_populates="station")


# ------------------- Trains -------------------
class Train(Base):
    __tablename__ = "trains"
    train_id = Column(Integer, primary_key=True, index=True)
    train_name = Column(String(100), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.route_id", ondelete="CASCADE"))  # <- add this
    train_no = Column(Integer)
    # relationships
    berth_classes = relationship("BerthClass", back_populates="train", cascade="all, delete-orphan")
    schedules = relationship("TrainSchedule", back_populates="train", cascade="all, delete-orphan")
    route_stations = relationship("RouteStation", back_populates="train", cascade="all, delete-orphan")
    availabilities = relationship("TrainSeatAvailability", back_populates="train")

# ------------------- Routes -------------------
class Route(Base):
    __tablename__ = "routes"
    route_id = Column(Integer, primary_key=True, index=True)
    source_station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"))
    destination_station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"))

    # relationships
    source_station = relationship("Station", foreign_keys=[source_station_id], back_populates="source_routes")
    destination_station = relationship("Station", foreign_keys=[destination_station_id], back_populates="destination_routes")


# ------------------- Route Stations -------------------
class RouteStation(Base):
    __tablename__ = "route_stations"
    route_station_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"))
    stop_number = Column(Integer, nullable=False)
    arrival_time = Column(Time)
    departure_time = Column(Time)
    distance_from_start_km = Column(Integer)

    # relationships
    train = relationship("Train", back_populates="route_stations")
    station = relationship("Station", back_populates="route_stations")


# ------------------- Berth Classes -------------------
class BerthClass(Base):
    __tablename__ = "berth_classes"
    berth_class_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    class_type = Column(String(50), nullable=False)
    total_berths = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    # relationships
    train = relationship("Train", back_populates="berth_classes")
    seat_availability = relationship("TrainSeatAvailability", back_populates="berth_class", cascade="all, delete-orphan")


# ------------------- Train Seat Availability -------------------
class TrainSeatAvailability(Base):
    __tablename__ = "train_seat_availability"
    availability_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id"), nullable=False)
    berth_class_id = Column(Integer, ForeignKey("berth_classes.berth_class_id", ondelete="CASCADE"))
    available_seats = Column(Integer, nullable=False)
    travel_date = Column(Date, nullable=False) 
    #total_berths = Column(Integer, nullable=False)
    # relationships
    train = relationship("Train", back_populates="availabilities")
    berth_class = relationship("BerthClass", back_populates="seat_availability")


# ------------------- Train Schedules -------------------
class TrainSchedule(Base):
    __tablename__ = "train_schedules"
    schedule_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    route_id = Column(Integer, ForeignKey("routes.route_id", ondelete="CASCADE"))
    station_id = Column(Integer, ForeignKey("stations.station_id", ondelete="CASCADE"))
    departure_time = Column(Time)
    arrival_time = Column(Time)
    # relationships
    train = relationship("Train", back_populates="schedules")


# ------------------- Passengers -------------------
class Passenger(Base):
    __tablename__ = "passengers"
    passenger_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)


# ------------------- Bookings -------------------
class Booking(Base):
    __tablename__ = "bookings"
    booking_id = Column(Integer, primary_key=True, index=True)
    passenger_id = Column(Integer, ForeignKey("passengers.passenger_id", ondelete="CASCADE"))
    train_id = Column(Integer, ForeignKey("trains.train_id", ondelete="CASCADE"))
    berth_class_id = Column(Integer, ForeignKey("berth_classes.berth_class_id", ondelete="CASCADE"))
    travel_date = Column(Date, nullable=False)
    seat_number = Column(Integer, nullable=False)
    status = Column(String(100), nullable=False)
    ticket_count = Column(Integer, nullable=False)
    # relationships
    passenger = relationship("Passenger")
    train = relationship("Train")
    berth_class = relationship("BerthClass")
