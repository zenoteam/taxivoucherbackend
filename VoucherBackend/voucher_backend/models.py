from datetime import datetime

from sqlalchemy import func

from voucher_backend.db import db


class VoucherModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driverId = db.Column(db.String(250), nullable=False)
    driverPhoneNumber = db.Column(db.String(250), nullable=False)
    pin = db.Column(db.String(250), nullable=False)
    amountBought = db.Column(db.Integer(), nullable=False)
    voucherWorth = db.Column(db.Integer(), nullable=False)
    discountAmount = db.Column(db.Integer(), nullable=True) 
    userPhoneNumber = db.Column(db.String(250), nullable=True)
    # not used = 1, used = 2
    status = db.Column(db.Integer, nullable=True)
    dateGenerated = db.Column(db.DateTime, server_default=func.now())
    timeUsed = db.Column(db.DateTime, nullable=True)


class DiscountModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discountPercent = db.Column(db.Float(), nullable=True) 
    timestamp = db.Column(db.DateTime, server_default=func.now())        
    updateTimeStamp = db.Column(db.DateTime, onupdate=func.now())


def register_discount():
    '''Register default discount'''

    existing_discount = DiscountModel.query.first()
    if existing_discount is None:
        discount = DiscountModel(discountPercent=0.2)
        db.add(discount)
        db.commit()  # Create new discount
        return(f"""Disount created""")
    else:
        return('Discount already exists')

if __name__ == '__main__':
    register_discount()