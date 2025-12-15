from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from database import Base


# ------------------- Stations -------------------
class Station(Base):
    __tablename__ = "polRail_stations_2"
    station_id = Column(Integer, primary_key=True, index=True)
    station_name = Column(String(100), unique=True, nullable=False)
    station_name_PL = Column(String(100), unique=True, nullable=False)
    station_name_comb_PL = Column(String(100), unique=True, nullable=False)
    station_id_code = Column(String(100), nullable=False)
    # relationships
    source_routes = relationship("Route", back_populates="source_station",
                                 foreign_keys="Route.source_station_id")
    destination_routes = relationship("Route", back_populates="destination_station",
                                      foreign_keys="Route.destination_station_id")
    route_stations = relationship("RouteStation", back_populates="station")


# ------------------- Trains -------------------
class Train(Base):
    __tablename__ = "polRail_trains_2"
    train_id = Column(Integer, primary_key=True, index=True)
    train_name = Column(String(100), nullable=False)
    train_type = Column(String(100), nullable=False)
    route_id = Column(Integer, ForeignKey("polRail_routes_2.route_id", ondelete="CASCADE"))  # <- add this
    train_no = Column(Integer)
    alternate_train_no = Column(Integer)
    # relationships
    berth_classes = relationship("BerthClass", back_populates="train", cascade="all, delete-orphan")
    schedules = relationship("TrainSchedule", back_populates="train", cascade="all, delete-orphan")
    route_stations = relationship("RouteStation", back_populates="train", cascade="all, delete-orphan")
    availabilities = relationship("TrainSeatAvailability", back_populates="train")

# ------------------- Routes -------------------
class Route(Base):
    __tablename__ = "polRail_routes_2"
    route_id = Column(Integer, primary_key=True, index=True)
    source_station_id = Column(Integer, ForeignKey("polRail_stations_2.station_id", ondelete="NO ACTION"))
    destination_station_id = Column(Integer, ForeignKey("polRail_stations_2.station_id", ondelete="CASCADE"))

    # relationships
    source_station = relationship("Station", foreign_keys=[source_station_id], back_populates="source_routes")
    destination_station = relationship("Station", foreign_keys=[destination_station_id], back_populates="destination_routes")


# ------------------- Route Stations -------------------
class RouteStation(Base):
    __tablename__ = "polRail_route_stations_2"
    route_station_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("polRail_trains_2.train_id", ondelete="NO ACTION"))
    station_id = Column(Integer, ForeignKey("polRail_stations_2.station_id", ondelete="CASCADE"))
    route_id = Column(Integer, ForeignKey("polRail_routes_2.route_id", ondelete="NO ACTION"))
    stop_number = Column(Integer, nullable=False)
    arrival_time = Column(Time)
    departure_time = Column(Time)
    distance_from_start_km = Column(Integer)

    # relationships
    train = relationship("Train", back_populates="route_stations")
    station = relationship("Station", back_populates="route_stations")


# ------------------- Berth Classes -------------------
class BerthClass(Base):
    __tablename__ = "polRail_berth_classes_2"
    berth_class_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("polRail_trains_2.train_id", ondelete="CASCADE"))
    class_type = Column(String(50), nullable=False)
    total_berths = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    # relationships
    train = relationship("Train", back_populates="berth_classes")
    seat_availability = relationship("TrainSeatAvailability", back_populates="berth_class", cascade="all, delete-orphan")


# ------------------- Train Seat Availability -------------------
class TrainSeatAvailability(Base):
    __tablename__ = "polRail_train_seat_availability_2"
    availability_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("polRail_trains_2.train_id"), nullable=False)
    berth_class_id = Column(Integer, ForeignKey("polRail_berth_classes_2.berth_class_id", ondelete="CASCADE"))
    available_seats = Column(Integer, nullable=False)
    travel_date = Column(Date, nullable=False) 
    #total_berths = Column(Integer, nullable=False)
    # relationships
    train = relationship("Train", back_populates="availabilities")
    berth_class = relationship("BerthClass", back_populates="seat_availability")


# ------------------- Train Schedules -------------------
class TrainSchedule(Base):
    __tablename__ = "polRail_train_schedules_2"
    schedule_id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("polRail_trains_2.train_id", ondelete="NO ACTION"))
    route_id = Column(Integer, ForeignKey("polRail_routes_2.route_id", ondelete="CASCADE"))
    station_id = Column(Integer, ForeignKey("polRail_stations_2.station_id", ondelete="NO ACTION"))
    departure_time = Column(Time)
    arrival_time = Column(Time)
    # relationships
    train = relationship("Train", back_populates="schedules")

'''
# ------------------- Passengers -------------------
class Passenger(Base):
    __tablename__ = "polRail_passengers"
    passenger_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)


# ------------------- Bookings -------------------
class Booking(Base):
    __tablename__ = "polRail_bookings"
    booking_id = Column(Integer, primary_key=True, index=True)
    passenger_id = Column(Integer, ForeignKey("polRail_passengers.passenger_id", ondelete="NO ACTION"))
    train_id = Column(Integer, ForeignKey("polRail_trains.train_id", ondelete="NO ACTION"))
    berth_class_id = Column(Integer, ForeignKey("polRail_berth_classes.berth_class_id", ondelete="CASCADE"))
    travel_date = Column(Date, nullable=False)
    seat_number = Column(Integer, nullable=False)
    status = Column(String(100), nullable=False)
    ticket_count = Column(Integer, nullable=False)
    # relationships
    passenger = relationship("Passenger")
    train = relationship("Train")
    berth_class = relationship("BerthClass")
'''