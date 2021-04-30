
import sys

# for creating the mapper code
from sqlalchemy import Column, ForeignKey, Integer, Float, String

# for configuration and class code
from sqlalchemy.ext.declarative import declarative_base

# for creating foreign key relationship between the tables
from sqlalchemy.orm import relationship

# for configuration
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# create declarative_base instance
Base = declarative_base()


# we create the class Book and extend it from the Base Class.
class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    topic = Column(String(250))
    stock = Column(Integer)
    cost = Column(Float)

    @property
    def serializeQueryByTopic(self):
        return {
            self.title:self.id,
        } 

    @property
    def serializeQueryById(self):
        return {
            "stock": self.stock,
            "cost": self.cost,
        }
    
    @property
    def serializeAll(self):
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "stock": self.stock,
            "cost": self.cost
        }

# creates a create_engine instance at the bottom of the file
engine = create_engine('sqlite:///books-collection.db')

Base.metadata.create_all(engine)

# Connect to Database and create database session
engine2 = create_engine('sqlite:///books-collection.db',
                       echo=True, connect_args={'check_same_thread': False})

Base.metadata.bind = engine2

DBSession = sessionmaker(bind=engine2)
session = DBSession()

