 
import certifi
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import yfinance as yf
from emails import StockEmail
from yFinanceTempFix.yfFix import YFinance
from database.basemodels import User, Stock


class DataBase:
    DB = None
    def __init__(self):
        uri = "mongodb+srv://stock-admin:secure_pass123@cluster0.csya3y9.mongodb.net/?retryWrites=true&w=majority"
        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'),tlsCAFile=certifi.where())
        DataBase.DB = client["StockDataBase"]
        self.collection = DataBase.DB["StockNames"]


    def get_stocks(self):
        self.collection = DataBase.DB["StockNames"]
        obj = self.collection.find_one()
        return(obj["stocks"])

    def get_verified_email(self, email: str):
        self.collection = DataBase.DB["VerifiedEmails"]
        existing_email = self.collection.find_one({'email': email}, {'_id': 0})
        return existing_email

    def add_verified_email(self, email:str):
        self.collection = DataBase.DB["VerifiedEmails"]
        if DataBase.get_verified_email(self, email):
            return False
        else:
            return self.collection.insert_one({'email': email}).inserted_id

    def store_verification_code(self, email: str, code: str):
        self.collection = DataBase.DB["VerificationCodes"]
        query = {"email": email}
        # Update or insert verification code into db
        return self.collection.update_one(query, {"$set": {'email': email,'code': code, 'timestamp': datetime.now()}}, upsert=True)


    def check_code_valid(self, email: str, code: str):
        self.collection = DataBase.DB["VerificationCodes"]
        query = {"email": email, "code": code}
        document = self.collection.find_one(query)
        if document:
            timestamp = document.get("timestamp")
            if timestamp and (datetime.now() - timestamp) < timedelta(minutes=5):
                self.collection.delete_one({ "_id": document.get('_id')})
                return True
        return False

    def insert_user_data(self,user:User, tickerToInsertUpdate: str):
        self.collection = DataBase.DB["UserInformation"]
        query = {"email": user.email}
        user_data = self.collection.find_one(query)
        if user_data:
            new_stock_list = { "$set": {f'stockList.{tickerToInsertUpdate}': Stock.model_dump(user.stockList[tickerToInsertUpdate])} }
            return self.collection.update_one(query, new_stock_list).modified_count
        else: 
            return self.collection.insert_one(user.model_dump()).inserted_id

    def delete_user_stock(self, email: str, stock: str):
        self.collection = DataBase.DB["UserInformation"]
        query = {"email": email, f'stockList.{stock}': {"$exists": True}}
        user_data = self.collection.find_one(query)
        if user_data:
            new_stock_list = { "$unset": {f'stockList.{stock}': ""} }
            return self.collection.update_one(query, new_stock_list)
        
     
    
    def get_user_data(self, email: str):
        self.collection = DataBase.DB["UserInformation"]
        query = {"email": email}
        user_data = self.collection.find_one(query)

        # Convert ObjectId to string
        if user_data and "_id" in user_data:
            user_data["_id"] = str(user_data["_id"])

        return user_data


    def update_stock_prices(self, stockName : str, currentPrice: float, thresholdValue : float, emailOfUser : str):
        obj = StockEmail()
        if currentPrice < thresholdValue:
            obj.reached_threshold_email(emailOfUser, stockName, thresholdValue)
            
            
    def getUserBase(self):
            self.collection = DataBase.DB["UserInformation"]
            updatedStockInfo = {}
            for eachUserDoc in self.collection.find():
                emailOfUser = eachUserDoc["email"]
                for eachUserStockParam in eachUserDoc["stockList"]:
                    nameOfStock = eachUserStockParam["name"]
                    # Only fetch stock data if not already fetched
                    if (nameOfStock not in updatedStockInfo):
                        updatedStockInfo[nameOfStock] = YFinance(nameOfStock)
                    currentPrice = float(updatedStockInfo[nameOfStock].info["currentPrice"])
                    print(nameOfStock)
                    thresholdValue = eachUserStockParam["threshold"]
                    self.update_stock_prices(nameOfStock,currentPrice, thresholdValue, emailOfUser)
