# config.py
import os
class Config:
    SECRET_KEY = "dev"
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"  # 先用本機檔案 DB
    SQLALCHEMY_TRACK_MODIFICATIONS = False

