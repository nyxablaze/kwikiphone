from flask import Flask, render_template, request
import sqlite3
import random


app = Flask(__name__)

@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

sql_commands = [
    '''CREATE TABLE IF NOT EXISTS PhoneModel (
        modelNumber TEXT,
        modelName TEXT,
        storage INTEGER,
        colour TEXT,
        baseCost REAL,
        dailyCost REAL,
        PRIMARY KEY (modelNumber, modelName)
    );''',
    
    '''CREATE TABLE IF NOT EXISTS Customer (
        customerId INTEGER PRIMARY KEY,
        customerName TEXT,
        customerEmail TEXT
    );''',

    '''CREATE TABLE IF NOT EXISTS Phone (
        modelNumber TEXT,
        modelName TEXT,
        IMEI TEXT PRIMARY KEY,
        FOREIGN KEY (modelNumber, modelName) REFERENCES PhoneModel(modelNumber, modelName),
        CHECK (
            (
                (
                    CAST(SUBSTR(IMEI, 1, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 3, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 5, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 7, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 9, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 11, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 13, 1) AS INTEGER) +
                    CAST(SUBSTR(IMEI, 15, 1) AS INTEGER)
                ) +
                (
                    CAST(SUBSTR(SUBSTR(IMEI, 2, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 2, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 4, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 4, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 6, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 6, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 8, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 8, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 10, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 10, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 12, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 12, 1) * 2, 2, 1) AS INTEGER) +
                    CAST(SUBSTR(SUBSTR(IMEI, 14, 1) * 2, 1, 1) AS INTEGER) + 
                    CAST(SUBSTR(SUBSTR(IMEI, 14, 1) * 2, 2, 1) AS INTEGER)
                )
            ) % 10 = 0
        )
    );''',

    '''CREATE TABLE IF NOT EXISTS rentalContract (
        customerId INTEGER,
        IMEI TEXT,
        dateOut TEXT,
        dateBack TEXT,
        rentalCost REAL,
        PRIMARY KEY (customerId, IMEI, dateOut),
        FOREIGN KEY (IMEI) REFERENCES Phone(IMEI) ON DELETE SET NULL ON UPDATE NO ACTION,
        FOREIGN KEY (customerId) REFERENCES Customer(customerId),
        CHECK (rentalCost >= 0)
    );''',

    '''CREATE TRIGGER IF NOT EXISTS costCalculation BEFORE UPDATE OF dateBack ON rentalContract
    BEGIN
        SELECT RAISE(ABORT, 'Date back cannot be before date out') WHERE (julianday(NEW.dateBack) - julianday(NEW.dateOut)) < 0;
        SELECT RAISE(ABORT, 'IMEI does not exist') WHERE (SELECT IMEI FROM Phone WHERE Phone.IMEI = NEW.IMEI) IS NULL;
        UPDATE rentalContract
        SET rentalCost = ROUND((
            ((julianday(NEW.dateBack) - julianday(NEW.dateOut) + 1) *
            (SELECT dailyCost FROM PhoneModel WHERE PhoneModel.modelNumber = (SELECT modelNumber FROM Phone WHERE Phone.IMEI = NEW.IMEI))) + 
            (SELECT baseCost FROM PhoneModel WHERE PhoneModel.modelNumber = (SELECT modelNumber FROM Phone WHERE Phone.IMEI = NEW.IMEI))
        ), 2)
        WHERE OLD.dateBack IS NULL AND rentalContract.IMEI = NEW.IMEI AND rentalContract.dateBack IS NULL;
    END;''',

    '''CREATE TRIGGER IF NOT EXISTS deleteIMEI BEFORE DELETE ON Phone
    BEGIN
        UPDATE rentalContract
        SET IMEI = NULL
        WHERE rentalContract.IMEI = OLD.IMEI;
        END;''',

    '''CREATE TRIGGER IF NOT EXISTS checkIMEIandCustomer BEFORE INSERT ON rentalContract
    BEGIN
        SELECT RAISE(ABORT, 'IMEI does not exist') WHERE (SELECT IMEI FROM Phone WHERE Phone.IMEI = NEW.IMEI) IS NULL;
        SELECT RAISE(ABORT, 'Customer does not exist') WHERE (SELECT customerId FROM Customer WHERE Customer.customerId = NEW.customerId) IS NULL;
        END;''',

    '''CREATE VIEW IF NOT EXISTS CustomerSummary AS
        SELECT customer.customerid, CASE WHEN Phone.modelName IS NOT NULL THEN Phone.modelName ELSE NULL END AS modelName, 
        SUM((julianday(rentalContract.dateBack) - julianday(rentalContract.dateOut) + 1)) AS daysRented, 
        strftime('%Y', dateBack, '-6 month') || '-' || strftime('%Y', dateBack, '-6 months', '+1 year') AS taxYear, 
        SUM(rentalcontract.rentalCost) AS rentalCost
        FROM customer INNER JOIN rentalContract ON customer.customerid = rentalContract.customerid LEFT JOIN Phone ON rentalContract.IMEI = Phone.IMEI
        WHERE rentalcontract.dateBack IS NOT NULL
        GROUP BY customer.customerid, modelName, taxYear;'''
]


for command in sql_commands:
    cursor.execute(command)
conn.execute("PRAGMA foreign_keys = ON;")

@app.route('/customerForm', methods=['GET', 'POST'])
def customerform():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        randid = random.randint(1000000, 9999999)
        with open('idlist.txt', 'w+') as f:
            idlist = f.readlines()
            if str(randid) in idlist:
                while str(randid) in idlist:
                    randid = random.randint(1000000, 9999999)
                f.write(str(randid) + '\n')
            else:
                f.write(str(randid) + '\n')
        with sqlite3.connect("data.db") as customers:
            cursor = customers.cursor()
            cursor.execute("INSERT INTO Customer (customerId, customerName, customerEmail) VALUES (?, ?, ?)", (randid, name, email))
            customers.commit()
        return render_template('index.html')
    else:
        return render_template('customerForm.html')
    
@app.route('/Customers')
def customers():
    connect = sqlite3.connect('data.db')
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Customer")

    data = cursor.fetchall()
    return render_template('Customers.html', data=data)

@app.route('/Phones')
def Phones():
    connect = sqlite3.connect('data.db')
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Phone")

    data = cursor.fetchall()
    return render_template('Phones.html', data=data)

@app.route('/phoneForm', methods=['GET', 'POST'])
def phoneForm():
    if request.method == 'POST':
        modelNumber = request.form['modelNumber']
        modelName = request.form['modelName']
        IMEI = request.form['IMEI']
        error = False

        try:
            with sqlite3.connect('data.db') as phone:
                cursor = phone.cursor()
                cursor.execute("INSERT INTO Phone (modelNumber, modelName, IMEI) VALUES (?, ?, ?)", (modelNumber, modelName, IMEI))
                return render_template('index.html')
        except: #
            error = True
            errorMessage = "An error occured, please ensure you are not entering a duplicate or invalid IMEI"
            return render_template('phoneForm.html', error=error, errorMessage=errorMessage)
    else: 
        return render_template('phoneForm.html')

@app.route('/phoneModels')
def phoneModels():
    connect = sqlite3.connect('data.db')
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM phoneModel")

    data = cursor.fetchall()
    return render_template('phoneModels.html', data=data)

@app.route('/modelForm', methods=['GET', 'POST'])
def modelForm():
    if request.method == 'POST':
        modelNumber = request.form['modelNumber']
        modelName = request.form['modelName']
        storage = request.form['storageCapacity']
        colour = request.form['colour']
        baseCost = request.form['baseCost']
        dailyCost = request.form['dailyCost']
        error = False

        try:
            with sqlite3.connect('data.db') as models:
                cursor = models.cursor()
                cursor.execute("INSERT INTO phoneModel (modelNumber, modelName, storage, colour, baseCost, dailyCost) VALUES (?, ?, ?, ?, ?, ?)", (modelNumber, modelName, storage, colour, baseCost, dailyCost))
                return render_template('index.html')
        except: #
            error = True
            errorMessage = 'An error occurred, please ensure you are not entering a duplicate phone model'
            return render_template('modelForm.html', error=error, errorMessage=errorMessage)
    else:
        return render_template('modelForm.html')

@app.route('/rentalContracts')
def rentalContracts():
    connect = sqlite3.connect('data.db')
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM rentalContract")

    data = cursor.fetchall()
    return render_template('rentalContracts.html', data=data)

@app.route('/newRentalForm', methods=['GET', 'POST'])
def newRentalForm():
    if request.method == 'POST':
        customerId = request.form['customerId']
        IMEI = request.form['IMEI']
        dateOut = request.form['dateOut']
        error = False

        try:
            with sqlite3.connect('data.db') as rentals:
                cursor = rentals.cursor()
                cursor.execute("INSERT INTO rentalContract VALUES(?, ?, ?, NULL, NULL)", (customerId, IMEI, dateOut,))
                return render_template('index.html')
        except:
            error = True
            errorMessage = 'An error occurred, please ensure the IMEI and customer ID are valid, and that the phone is not already rented out'
            print('an error occured, check inputs')
            return render_template('newcontractForm.html', error=error, errorMessage=errorMessage)
    else:
        return render_template('newcontractForm.html')
    
@app.route('/updatecontractForm', methods=['GET', 'POST'])
def updatecontractForm():
    if request.method == 'POST':
        dateBack = request.form['dateBack']
        IMEI = request.form['IMEI']
        error = False

        try:
            with sqlite3.connect('data.db') as rentals:
                cursor = rentals.cursor()
                cursor.execute("UPDATE rentalContract SET dateBack = ? WHERE IMEI = ? AND dateBack IS NULL", (dateBack, IMEI))
                return render_template('index.html')
        except:
            error = True
            errorMessage = 'An error occurred, please ensure the IMEI is valid and the phone is currently rented out'
            print('an error occured, check inputs')
            return render_template('updatecontractForm.html', error=error, errorMessage=errorMessage)
    else:
        return render_template('updatecontractForm.html')
    
@app.route('/deletePhoneForm', methods=['GET', 'POST'])
def deletePhoneForm():
    if request.method == "POST":
        IMEI = request.form['IMEI']
        error = False

        try:
            with sqlite3.connect('data.db') as phones:
                cursor = phones.cursor()
                cursor.execute("DELETE FROM Phone WHERE IMEI = ?", (IMEI,))
                return render_template('index.html')
        except:
            errror = True
            errorMessage = 'An error occurred, please ensure the IMEI is valid and exists in the database'
            # An assumption was made here that the phone will never be deleted while rented out, as this operation is performed by an admin.
            print('an error occured, check inputs')
            return render_template('deletePhoneForm.html', error=error, errorMessage=errorMessage)
    else:
        return render_template('deletePhoneForm.html')
    
@app.route('/view')
def view():
    connect = sqlite3.connect('data.db')
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM CustomerSummary")

    data = cursor.fetchall()
    return render_template('view.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
