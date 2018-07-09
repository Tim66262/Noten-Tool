from django.shortcuts import render
from django.shortcuts import redirect
import pyrebase
from django.contrib import auth

#Firebase Configs
from requests import HTTPError

config = {
  'apiKey': "AIzaSyCu-oLiIy_hfrW4Z-jWOznBdooEEzD3im8",
  'authDomain': "notentool-39aa3-1574c.firebaseapp.com",
  'databaseURL': "https://notentool-39aa3-1574c.firebaseio.com",
  'projectId': "notentool-39aa3",
  'storageBucket': "notentool-39aa3.appspot.com",
  'messagingSenderId': "1028209732457"
}


#Firebase Connection
firebase = pyrebase.initialize_app(config)
#Firebase Connection to the Database
database = firebase.database()
#Firebase Connection to the Authentification
authentification = firebase.auth()


#Destroy the Session and render the home page
def home(request):
    auth.logout(request)
    return render(request, "home.html")


#Render the Login Page
def signIn(request):
    return render(request, "signIn.html")


#Get the email and pw out of the Post and try to login in db. Start Session and tore the UID
def postsign(request):

    email = request.POST.get('email')
    password = request.POST.get('password')

    try:
        user = authentification.sign_in_with_email_and_password(email, password)
    except:
        message = "Kein Account gefunden"
        return render(request, "signIn.html", {"message": message})

    session_id = user['idToken']
    request.session['uid'] = str(session_id)
    return redirect('overview')


#Load all Lists where permission is allow
def overview(request):
    idtoken = request.session['uid']
    a = authentification.get_account_info(idtoken)
    a = a['users']
    a = a[0]
    localid = a['localId']

    data = database.child('users').child(localid).child('authorization').shallow().get().val()
    peoplelist = []

    for i in data:
        userid = database.child('users').child(localid).child('authorization').child(i).get().val()
        person = database.child('users').child(userid).child('email').get().val()
        peoplelist.append(Person(userid, person))

    return render(request, "overview.html", {"people": peoplelist})


def years(request, id):
    #Get the email of the user
    email = database.child('users').child(id).child('email').get().val()
    #Get all years of the user in bad format
    yearsUnsorted = database.child('users').child(id).child('grades').get().val()
    #Convert it to goo format
    yearsSorted = []
    if yearsUnsorted != None:
        if isinstance(yearsUnsorted, list):
            counter = 0
            print(yearsUnsorted)
            for i in yearsUnsorted:
                if i != None:
                    yearsSorted.append(counter)
                counter = counter + 1
        else:
            for key, value in yearsUnsorted.items():
                yearsSorted.append(key)
    #Look if the user is the owner
    idtoken = request.session['uid']
    a = authentification.get_account_info(idtoken)
    a = a['users']
    a = a[0]
    localid = a['localId']
    if localid == id:
        isOwner = True
    else:
        isOwner = False
    return render(request, "years.html", {"uid": id, "email": email, "years": yearsSorted, "isOwner": isOwner})


def semesters(request, id, year):
    email = database.child('users').child(id).child('email').get().val()
    semestersUnsorted = database.child('users').child(id).child('grades').child(year).get().val()
    semestersSorted = []
    if semestersUnsorted != None:
        counter = 0
        for i in semestersUnsorted:
            if i != None:
                semestersSorted.append(counter)
            counter = counter + 1

    return render(request, "semesters.html", {"id": id, "email": email, "year": year, "semesters": semestersSorted})


def subjects(request, id, year, semester):
    #Get all subjects by id, year and semester.
    facher = database.child('users').child(id).child('grades').child(year).child(semester).get().val()
    notenliste = []
    if facher:
        for fach in facher:
            noten = database.child('users').child(id).child('grades').child(year).child(semester).child(fach).get().val()
            fach = Fach(fach)
            for note in noten:
                if note:
                    gewichtung = note['gewichtung']
                    wert = note['wert']
                    fach.addGrade(Note(wert, gewichtung))
            if fach.gradeList:
                fach.calculateAverage()
            else:
                fach.average = "No Grade Detected"
            notenliste.append(fach)
    #Look if the user is the owner
    idtoken = request.session['uid']
    a = authentification.get_account_info(idtoken)
    a = a['users']
    a = a[0]
    localid = a['localId']
    if localid == id:
        isOwner = True
    else:
        isOwner = False
    return render(request, "subjects.html", {"id": id, "year": year, "semester": semester, "notenliste": notenliste, "isOwner": isOwner})


def saveyear(request):
    idtoken = request.session['uid']
    a = authentification.get_account_info(idtoken)
    a = a['users']
    a = a[0]
    id = a['localId']

    year = request.POST.get('year')
    if year:
        recordedYears = database.child('users').child(id).child('grades').get().val()
        if recordedYears:
            for recordedYear in recordedYears:
                if recordedYear == year:
                    return redirect('years', id=id)

        database.child('users').child(id).child('grades').child(year).child(1).set("")
        database.child('users').child(id).child('grades').child(year).child(2).set("")
    return redirect('years', id=id)


def addSubject(request, id, year, semester):
    subjectname = request.POST.get('subjectname')
    if subjectname:
        try:
            database.child('users').child(id).child('grades').child(year).child(semester).child(subjectname).set("")
        except HTTPError:
            print("Ups")
    return redirect('subjects', id, year, semester)


def deleteSubject(request, id, year, semester, subject):
    database.child('users').child(id).child('grades').child(year).child(semester).child(subject).set(None)
    semester1 = database.child('users').child(id).child('grades').child(year).child(1).get().val()
    semester2 = database.child('users').child(id).child('grades').child(year).child(2).get().val()
    if not semester1:
        database.child('users').child(id).child('grades').child(year).child(1).set("")
    if not semester2:
        database.child('users').child(id).child('grades').child(year).child(2).set("")

    return redirect('subjects', id, year, semester)


def addGrade(request, id, year, semester, subject):
    massvalue = request.POST.get('massvalue')
    if(massvalue == "0.5"):
        massvalue = float(massvalue)
    else:
        massvalue = int(massvalue)
    gradevalue = float(request.POST.get('gradevalue'))
    if massvalue and gradevalue:
        try:
            items = database.child('users').child(id).child('grades').child(year).child(semester).child(subject).get().val()
            counter = 0
            if items:
                for item in items:
                    if not item:
                        break
                    else:
                        counter = counter + 1
            database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).child('wert').set(gradevalue)
            database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).child('gewichtung').set(massvalue)
        except HTTPError:
            print("Ups")
    return redirect('subjects', id, year, semester)


def updateGrade(request, id, year, semester, subject, wertOld, gewichtungOld):
    wertNew = float(request.POST.get('wert'))
    gewichtungNew = float(request.POST.get('gewichtung'))
    noten = database.child('users').child(id).child('grades').child(year).child(semester).child(subject).get().val()
    counter = 0

    for note in noten:
        if str(note["wert"]) == str(wertOld) and str(note["gewichtung"]) == str(gewichtungOld):
            print("oge")
            break
        counter = counter + 1
    if counter < len(noten):
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).update({"wert": wertNew})
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).update({"gewichtung": gewichtungNew})
    return redirect('subjects', id, year, semester)


def deleteGrade(request, id, year, semester, subject, wert, gewichtung):
    noten = database.child('users').child(id).child('grades').child(year).child(semester).child(subject).get().val()
    if len(noten) == 1:
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).set("")
    else:
        counter = 0
        for note in noten:
            if note:
                if float(note['wert']) == float(wert) and float(note['gewichtung']) == float(gewichtung):
                    database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).set(None)
                    break
            counter = counter + 1
    return redirect('subjects', id, year, semester)


#Logout function
def logout(request):
    auth.logout(request)
    return redirect('signIn')


#Definition of Python Objects

class Person:
    def __init__(self, id, email):
        self.id = id
        self.email = email


class Fach:
    def __init__(self, name):
        self.name = name
        self.gradeList = []
        self.average = None

    def addGrade(self, grade):
        self.gradeList.append(grade)

    def calculateAverage(self):
        result = 0
        counter = 0
        for note in self.gradeList:
            result = result + note.wert * note.gewichtung * 2
            counter = counter + note.gewichtung * 2
        result = round(result / counter, 2)
        self.average = result


class Note:
    def __init__(self, wert, gewichtung):
        self.wert = wert
        self.gewichtung = gewichtung