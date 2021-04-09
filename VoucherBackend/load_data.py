from voucher_backend.app import create_app
from voucher_backend.models import DiscountModel
from datetime import datetime

if __name__ == '__main__':
    application = create_app()
    application.app_context().push()
    
    print(DiscountModel.query.first())
    
    if not DiscountModel.query.first():
        # Create some test data
        test_data = [
            # for promo service
            ( 0.2, datetime.now(), datetime.now()),
        ]
        for discountPercent, timestamp, updateTimeStamp in test_data:
            discount = DiscountModel(
                discountPercent=discountPercent,
                timestamp=timestamp,
                updateTimeStamp=updateTimeStamp,
            )
            application.db.session.add(discount)

            application.db.session.commit()
            print("discount")
    
