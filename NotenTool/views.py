from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib import auth
import pyrebase

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


#Load all Lists where permission is allow
def overview(request):
    #Get the localId of the user
    idtoken = request.session['uid']
    a = authentification.get_account_info(idtoken)
    a = a['users']
    a = a[0]
    localid = a['localId']

    #Get the authorized People
    data = database.child('users').child(localid).child('authorization').shallow().get().val()

    #Genereate Person Object of the authorized People
    peoplelist = []
    for i in data:
        userid = database.child('users').child(localid).child('authorization').child(i).get().val()
        person = database.child('users').child(userid).child('email').get().val()
        peoplelist.append(Person(userid, person))

    #Render the overview
    return render(request, "overview.html", {"people": peoplelist})


#Show all years of a specific user
def years(request, id):
    #Get the email of the user
    email = database.child('users').child(id).child('email').get().val()
    #Get all years of the user in bad format
    yearsUnsorted = database.child('users').child(id).child('grades').get().val()
    #Convert it to readable format
    yearsSorted = []
    if yearsUnsorted != None:
        if isinstance(yearsUnsorted, list):
            counter = 0
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


#Show all semesters of a specific user in a specific year
def semesters(request, id, year):
    #Get all semesters and show them
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


#Show all Subjects and grades of an semester in an of a user
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


#Get the email and pw out of the Post and try to login in db. Start Session and tore the UID
def postsign(request):
    #Get the email and the passwort out of the Post
    email = request.POST.get('email')
    password = request.POST.get('password')

    #Try to authenificate the user. Else Error Message
    try:
        user = authentification.sign_in_with_email_and_password(email, password)
    except:
        messages.info(request, 'No Account Found')
        return render(request, "signIn.html")

    #Write the idToken to the session
    session_id = user['idToken']
    request.session['uid'] = str(session_id)

    #Redirect to the Overview page
    return redirect('overview')


#Logout function
def logout(request):
    auth.logout(request)
    return redirect('signIn')


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
                    messages.info(request, 'The Year already exists')
                    return redirect('years', id=id)

        database.child('users').child(id).child('grades').child(year).child(1).set("")
        database.child('users').child(id).child('grades').child(year).child(2).set("")
    return redirect('years', id=id)


#Add a Subject
def addSubject(request, id, year, semester):
    subjectname = request.POST.get('subjectname')
    #Check if Subject already exists
    facher = database.child('users').child(id).child('grades').child(year).child(semester).get().val()
    for fach in facher:
        if fach == subjectname:
            messages.info(request, 'Subject already exists')
            return redirect('subjects', id, year, semester)
    if subjectname:
        try:
            database.child('users').child(id).child('grades').child(year).child(semester).child(subjectname).set("")
        except HTTPError:
            print("Ups")
    return redirect('subjects', id, year, semester)


#Delete an Subject
def deleteSubject(request, id, year, semester, subject):
    #Delete the subjects
    database.child('users').child(id).child('grades').child(year).child(semester).child(subject).set(None)
    #Get the semesters
    semester1 = database.child('users').child(id).child('grades').child(year).child(1).get().val()
    semester2 = database.child('users').child(id).child('grades').child(year).child(2).get().val()
    #Set Values of semester to "" if they are empty
    if not semester1:
        database.child('users').child(id).child('grades').child(year).child(1).set("")
    if not semester2:
        database.child('users').child(id).child('grades').child(year).child(2).set("")

    return redirect('subjects', id, year, semester)


#Ad an grade
def addGrade(request, id, year, semester, subject):
    #Convert the value to Float if dezimal else to int (ugly)
    massvalue = request.POST.get('massvalue')
    if(massvalue == "0.5"):
        massvalue = float(massvalue)
    else:
        massvalue = int(massvalue)
    gradevalue = float(request.POST.get('gradevalue'))
    #Add the values to the Database
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
    #Render the subjects
    return redirect('subjects', id, year, semester)


#Update an Grade
def updateGrade(request, id, year, semester, subject, wertOld, gewichtungOld):
    #Get the values of the Grades
    wertNew = float(request.POST.get('wert'))
    gewichtungNew = float(request.POST.get('gewichtung'))
    noten = database.child('users').child(id).child('grades').child(year).child(semester).child(subject).get().val()
    counter = 0

    #Loop and count until the grade get found on db
    for note in noten:
        if str(note["wert"]) == str(wertOld) and str(note["gewichtung"]) == str(gewichtungOld):
            break
        counter = counter + 1

    #Check if a grade got found
    if counter < len(noten):
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).update({"wert": wertNew})
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).update({"gewichtung": gewichtungNew})
    return redirect('subjects', id, year, semester)


#Delete an grade
def deleteGrade(request, id, year, semester, subject, wert, gewichtung):
    #Get all Grades
    noten = database.child('users').child(id).child('grades').child(year).child(semester).child(subject).get().val()
    #If the length is One then delete the first Element
    if len(noten) == 1:
        database.child('users').child(id).child('grades').child(year).child(semester).child(subject).set("")
    #Else Loop until the right grade got found
    else:
        counter = 0
        for note in noten:
            if note:
                if float(note['wert']) == float(wert) and float(note['gewichtung']) == float(gewichtung):
                    database.child('users').child(id).child('grades').child(year).child(semester).child(subject).child(counter).set(None)
                    break
            counter = counter + 1
    return redirect('subjects', id, year, semester)


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