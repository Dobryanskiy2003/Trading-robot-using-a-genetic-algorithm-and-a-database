# database.py
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime

# Определяем базу данных и создаем подключение
DATABASE_URL = 'sqlite:///stocks.db'
Base = declarative_base()

class StockData(Base):
    __tablename__ = 'stock_data'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)

# Инициализация базы данных
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def load_data_to_db(file_path):
    """Загрузка данных из текстового файла в базу данных."""
    session = Session()
    
    # Очистка существующих данных перед загрузкой новых
    session.query(StockData).delete()
    session.commit()
    
    df = pd.read_csv(file_path, sep='\t', parse_dates=['DATETIME'])
    for _, row in df.iterrows():
        stock_data = StockData(
            date=row['DATETIME'],
            open_price=row['<OPEN>'],
            high_price=row['<HIGH>'],
            low_price=row['<LOW>'],
            close_price=row['<CLOSE>'],
            volume=row['<VOL>']
        )
        session.add(stock_data)
    session.commit()
    session.close()

def fetch_data_from_db():
    """Извлечение данных из базы данных."""
    session = Session()
    result = session.query(StockData).all()
    data = [(record.date, record.open_price, record.high_price, 
             record.low_price, record.close_price, record.volume) for record in result]
    session.close()
    return data