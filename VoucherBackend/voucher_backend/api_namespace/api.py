import http.client
import os
from datetime import datetime, timedelta
from uuid import uuid4
import random
import string


from flask import abort
from flask_restplus import Namespace, Resource, fields
import requests
from sqlalchemy import func

from voucher_backend import config
from voucher_backend.db import db
from voucher_backend.models import VoucherModel, DiscountModel
from voucher_backend.token_validation import validate_token_header


WALLET_SERVICE = os.environ.get("WALLET_SERVICE")

api = Namespace('api', description='General API operations')


def authentication_header_parser(value):
    payload = validate_token_header(value, config.PUBLIC_KEY)
    if payload is None:
        abort(401)
    return payload


def check_admin_return_payload(parser):
    args = parser.parse_args()
    tokenPayload = authentication_header_parser(args['Authorization'])

    # check if user is an admin
    if 'admin' not in tokenPayload:
        abort(403)

    return tokenPayload

def generate_pin():
    pin = ''
    for j in range(2):
        pin += random.choice(string.ascii_lowercase)
    for i in range(4):
        pin += str(random.randint(0,9))
    anypin = VoucherModel.query.filter(VoucherModel.pin==pin).first()
    if anypin:
        generate_pin()
    return pin


# Output formats
modelvoucher = {
    'id': fields.Integer(),
    'driverId': fields.String(),
    'driverPhoneNumber': fields.String(),
    'pin': fields.String(),
    'amountBought': fields.Integer(),
    'voucherWorth': fields.Integer(),
    'discountAmount': fields.Integer(),
    'userPhoneNumber': fields.String(),
    'status': fields.Integer(),
    'dateGenerated': fields.DateTime(),
    'dateUsed': fields.DateTime(),
}
voucherModel = api.model('Voucher', modelvoucher)

modeldiscount = {
    'id': fields.Integer(),
    'authId': fields.String(),
    'discountPercent': fields.Float(),
    'timestamp': fields.DateTime(),
    'updateTimeStamp': fields.DateTime(),
}
discountModel = api.model('Discount', modeldiscount)

# Input formats
authenticationParser = api.parser()
authenticationParser.add_argument(
    'Authorization',
    location='headers',
    type=str,
    help='Bearer Access Token'
)


discountParser = authenticationParser.copy()
discountParser.add_argument(
    'discountPercent',
    type=float,
    required=True,
    help='The Discount'
)
updateDiscountParser = discountParser.copy()

voucherParser = authenticationParser.copy()
voucherParser.add_argument(
    'driverPhoneNumber',
    type=str,
    required=True,
    help='The Drivers Phone Number'
)
voucherParser.add_argument(
    'amountBought',
    type=int,
    required=False,
    help='The amount paid by a driver for a voucher'
)
voucherParser.add_argument(
    'voucherWorth',
    type=int,
    required=True,
    help='The vocher worth'
)


updateVoucherParser = authenticationParser.copy()

updateVoucherParser.add_argument(
    'userPhoneNumber',
    type=str,
    required=False,
    help='The phone number of the user'
)

filterParser = authenticationParser.copy()
filterParser.add_argument(
    'id',
    type=str,
    location='args',
    help='Filter by voucher id'
)
filterParser.add_argument(
    'driverId',
    type=str,
    location='args',
    help='Filter by driver id'
)
filterParser.add_argument(
    'driverPhoneNumber',
    type=str,
    location='args',
    help='Filter by driver phone Number'
)
filterParser.add_argument(
    'minvoucherWorth',
    type=str,
    location='args',
    help='Filter by the worth of the voucher (minimum)'
)
filterParser.add_argument(
    'maxivoucherWorth',
    type=str,
    location='args',
    help='Filter by the worth of the voucher (maximum)'
)
filterParser.add_argument(
    'mindiscountAmount',
    type=str,
    location='args',
    help='Filter by the discount(minimum)'
)
filterParser.add_argument(
    'maxidiscountAmount',
    type=str,
    location='args',
    help='Filter by the discount (maximum)'
)

filterParser.add_argument(
    'status',
    type=int,
    choices=(1, 2),
    location='args',
    help='Filter by status of the voucher, 1-> Not Used, 2-> Used'
)
filterParser.add_argument(
    'userPhoneNumber',
    type=str,
    location='args',
    help='Filter by phone number of the user'
)


dateQuery_parser = authenticationParser.copy()
dateQuery_parser.add_argument(
    'startdate',
    type=str,
    required=True,
    help="The start date format '%d/%m/%Y'"
)
dateQuery_parser.add_argument(
    'enddate',
    type=str,
    required=True,
    help="The end date format '%d/%m/%Y'"
)

monthQuery_parser = authenticationParser.copy()
monthQuery_parser.add_argument(
    'year',
    type=str,
    required=True,
    help='The year'
)


@api.route('/vouchers/<int:pageNumber><int:noPerPage>')
class VehicleList(Resource):
    @api.doc('list_vouchers')
    @api.marshal_with(voucherModel, as_list=True)
    @api.expect(filterParser)
    def get(self, pageNumber:int, noPerPage:int):
        """
        Retrieve all vouchers
        """
        # authenticate bearer token
        args = filterParser.parse_args()
        authentication_header_parser(args['Authorization'])

        query = VoucherModel.query

        # filtering
        if args['id']:
            query = (
                query.filter(VoucherModel.id == args['id'])
            )
        if args['driverId']:
            query = (
                query.filter(VoucherModel.driverId == args['driverId'])
            )
        if args['driverPhoneNumber']:
            query = (
                query.filter(VoucherModel.driverPhoneNumber == args['driverPhoneNumber'])
            )
        if args['userPhoneNumber']:
            query = (
                query.filter(VoucherModel.userPhoneNumber == args['userPhoneNumber'])
            )
        if args['mindiscountAmount']:
            query = (
                query.filter(VoucherModel.discountAmount >= args['mindiscountAmount'])
            )
        if args['maxidiscountAmount']:
            query = (
                query.filter(VoucherModel.discountAmount <= args['maxidiscountAmount'])
            )
        if args['minvoucherWorth']:
            query = (
                query.filter(VoucherModel.voucherWorth >= args['minvoucherWorth'])
            )
        if args['maxivoucherWorth']:
            query = (
                query.filter(VoucherModel.voucherWorth <= args['maxivoucherWorth'])
            )
        if args['status']:
            query = (
                query.filter(VoucherModel.status == args['status'])
                )

        offset = (pageNumber - 1) * noPerPage 
        query = query.order_by('id')
        vouchers = query.offset(offset).limit(noPerPage)

        return list(vouchers), http.client.OK

@api.route('/vouchers/')
class VoucherPost(Resource):
    @api.doc('add_voucher')
    @api.expect(voucherParser)
    def post(self):
        """
        Add voucher.
        """

        # authenticate bearer token
        args = voucherParser.parse_args()
        tokenPayload = authentication_header_parser(args['Authorization'])
        auth_id = tokenPayload['auth_id']
        
        pin = generate_pin()
        
        discount = DiscountModel.query.get(1).discountPercent
        
        if not args["amountBought"]:
            amountBought = int( (1- discount) * args["voucherWorth"])
        else:
            amountBought = args["amountBought"]
            
        headers = {
            "Authorization": args["Authorization"]
        }
            
        data = {
            "amount": amountBought,
            "phoneNo": args["driverPhoneNumber"],
            "desc": "Voucher Purchase By Driver"
        }
        url = WALLET_SERVICE + "api/purchaseVoucher/"
        print(url)
        res = requests.post(headers=headers, data=data, url=url)
        
        if res.status_code != 201:
            return res.json(), res.status_code
        
        voucher = VoucherModel(
            driverId=auth_id,
            driverPhoneNumber=args['driverPhoneNumber'],
            pin=pin,
            amountBought=amountBought,
            voucherWorth=args['voucherWorth'],
            status=1
        )
   
        db.session.add(voucher)
        db.session.commit()

        result = api.marshal(voucher, voucherModel)
        return result, http.client.CREATED

@api.route('/vouchers/<int:voucherId>/')
class VoucherGetById(Resource):
    @api.doc('retrieve voucher with id')
    @api.marshal_with(voucherModel)
    @api.expect(authenticationParser)
    def get(self, voucherId: int):
        """
        Retrieve a specific voucher using pin
        """
        args = authenticationParser.parse_args()
        authentication_header_parser(args['Authorization'])

        voucher = VoucherModel.query.get(voucherId)
        if not voucher:
            # The voucher does not exist
            return '', http.client.NOT_FOUND

        return voucher

@api.route('/vouchers/buy/<string:voucherPin>/')
class VoucherSell(Resource):
    @api.doc('update_voucher')
    @api.expect(updateVoucherParser)
    def put(self, voucherPin: str):
        """
        Sell Voucher to Riders
        """

        # authenticate bearer token

        args = updateVoucherParser.parse_args()
        
        auth_id = authentication_header_parser(args['Authorization'])['auth_id']

        # todo: ask if only creators can update voucher

        voucher = VoucherModel.query.filter(VoucherModel.pin==voucherPin).first()

        if not voucher:
            # The voucher does not exist
            return {"status" :"error", "message": "Not Found"}, http.client.NOT_FOUND

        
        if voucher.status == 2:
            return {"status" :"error", "message": "Voucher Sold"}, http.client.OK

        # add voucher
        
        headers = {
            "Authorization": args["Authorization"]
        }
            
        data = {
            "amount": voucher.voucherWorth,
            "phoneNo": args['userPhoneNumber'],
            "desc": "Voucher Purchase By Rider"
        }
        url = WALLET_SERVICE + "api/topupwallet/"
        res = requests.post(headers=headers, data=data, url=url)
        
        if res.status_code != 201:
            return res.json(), res.status_code
        
       
        voucher.status = 2
        voucher.userPhoneNumber = args['userPhoneNumber'] or voucher.userPhoneNumber
        voucher.dateUsed = datetime.now() or voucher.dateUsed

        db.session.add(voucher)
        db.session.commit()

        result = api.marshal(voucher, voucherModel)
        return result, http.client.OK


@api.route('/me/')
class VoucherGetByAuth(Resource):
    @api.doc('retrieve voucher with auth id')
    @api.marshal_with(voucherModel)
    @api.expect(authenticationParser)
    def get(self):
        """
        Retrieve a specific voucher using auth id
        """
        args = authenticationParser.parse_args()
        auth_id = authentication_header_parser(args['Authorization'])['auth_id']

        vouchers = VoucherModel.query.filter(VoucherModel.driverId==auth_id).all()
        if not vouchers:
            # The voucher does not exist
            return '', http.client.NOT_FOUND

        return list(vouchers)


@api.route('/vouchers/pin/<string:voucherPin>/')
class VoucherGetByPin(Resource):
    @api.doc('retrieve voucher with pin')
    @api.marshal_with(voucherModel)
    @api.expect(authenticationParser)
    def get(self, voucherPin: str):
        """
        Retrieve a specific voucher using pin
        """
        args = authenticationParser.parse_args()
        authentication_header_parser(args['Authorization'])

        voucher = VoucherModel.query.filter(VoucherModel.pin==voucherPin).first()
        if not voucher:
            # The voucher does not exist
            return '', http.client.NOT_FOUND

        return voucher


@api.route('/discount/')
class DiscountGet(Resource):
    @api.doc('retrieve discount')
    #@api.marshal_with(discountModel)
    @api.expect(authenticationParser)
    def get(self):
        """
        Retrieve the discount
        """
        args = authenticationParser.parse_args()
        authentication_header_parser(args['Authorization'])

        discount = DiscountModel.query.get(1)
        if not discount:
            response = {
                "status":"error",
                "message":"No Discount"
            }
            # The discount does not exist
            return response, http.client.NOT_FOUND

        result = api.marshal(discount, discountModel)
        return result, http.client.OK

    @api.doc('update discount')
    @api.expect(updateDiscountParser)
    @api.marshal_with(discountModel, code=http.client.OK)
    def put(self):
        """
        Update discount.
        """
        # authenticate bearer token
        args = updateDiscountParser.parse_args()
        payload = authentication_header_parser(args['Authorization'])    
        auth_id = payload['auth_id']

        # todo: ask if only creators can update voucher

        discount = DiscountModel.query.get(1)

        if not discount:
            # The discount does not exist
            return '', http.client.NOT_FOUND

   
        # to check if discount percent has changed

        oldDiscountPercent = discount.discountPercent

        if oldDiscountPercent == args['discountPercent']:
            response = {
                "status":"error",
                "message":"new discount is the same with previous"
            }
            return response, http.client.BAD_REQUEST

        # update discount
       
        discount.authId = auth_id
        discount.discountPercent = args['discountPercent']

        db.session.add(discount)
        db.session.commit()

        result = api.marshal(discount, discountModel)
        return result, http.client.OK

    

@api.route('/stat/sumquery/')
class VoucherSummaryQuery(Resource):
    @api.doc('query count in db: total count')
    @api.expect(authenticationParser)
    def get(self):
        """
        Help find total count of vouchers in the database
        """
        args = authenticationParser.parse_args()
        authentication_header_parser(args['Authorization'])

        count = (VoucherModel.query.count())
        return count


@api.route('/stat/datequery/')
class VoucherDateQuery(Resource):
    @api.doc('query count in db: daily')
    @api.expect(dateQuery_parser)
    def get(self):
        """
        Help find the daily count of vouchers created within a range of dates
        """
        args = dateQuery_parser.parse_args()
        authentication_header_parser(args['Authorization'])

        start_date_str = args['startdate']
        end_date_str = args['enddate']

        start_date = datetime.strptime(start_date_str, "%d/%m/%Y").date()
        end_date = datetime.strptime(end_date_str, "%d/%m/%Y").date()

        result = {}

        if start_date > end_date:
            return '', http.client.BAD_REQUEST

        while start_date <= end_date:
            vouchers = (
                db.session.query(
                    func.count(VoucherModel.id)).filter(
                        func.date(VoucherModel.timestamp) == start_date
                    ).all()
            )
            date = start_date.strftime("%d/%m/%Y")
            result[date] = vouchers[0][0]

            start_date = start_date + timedelta(days=1)

        return result


@api.route('/stat/monthquery/')
class VoucherModelMonthQuery(Resource):
    @api.doc('query count in db: monthly')
    @api.expect(monthQuery_parser)
    def get(self):
        """
        Help find the daily count of vouchers created within a range of month
        """
        args = monthQuery_parser.parse_args()
        authentication_header_parser(args['Authorization'])

        str_year = args['year']
        try:
            year = int(str_year)
        except ValueError:
            return '', http.client.BAD_REQUEST

        result = {}

        if year < 2020:
            return '', http.client.BAD_REQUEST

        for month in range(1, 13):
            vouchers = (
                db.session.query(func.count(VoucherModel.id)).filter(
                    func.extract('year', VoucherModel.timestamp) == year).filter(
                        func.extract('month', VoucherModel.timestamp) == month
                    ).all()
            )

            result[f'{month}'] = vouchers[0][0]

        return result
