

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import select
from pgvector.sqlalchemy import Vector
from pgvector.sqlalchemy import Vector
import dotenv
import os


dotenv.load_dotenv()






DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

Session = sessionmaker(bind=engine, 
                        autocommit=False, 
                        autoflush=False)

Session = Session()
Base = declarative_base()





class Chunks_table(Base):
    __tablename__ = 'chunks_table'
    id = Column(Integer, primary_key=True)
    user = Column(String)
    section = Column(String)
    chunk = Column(String)
    document = Column(String)    
    embedding = Column(Vector(1024))

    def __repr__(self):
        return f"<Chunk(id={self.id}, chunk={self.chunk}, document={self.document}, embedding={self.embedding})>"
    

    
class diff_table(Base): 
    __tablename__ = 'diff_table'
    id = Column(Integer, primary_key=True)
    user = Column(String)
    section = Column(String)
    difference = Column(String)


    def __repr__(self):
        return f"<Summary(id={self.id}, section={self.section}, difference={self.difference})>"





Base.metadata.create_all(engine)


    




    




