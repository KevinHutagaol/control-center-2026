import sys
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QMainWindow
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
import pyrebase
import random
import UI.resource

firebaseConfig = { "apiKey": "AIzaSyAO1TlkKSTxIcQ6fxHGqtbb8j1TPNFhq8Y",
    "authDomain": "state-space-controller-design.firebaseapp.com",
    "projectId": "state-space-controller-design",
    "storageBucket": "state-space-controller-design.firebasestorage.app",
    "messagingSenderId": "491204843035",
    "appId": "1:491204843035:web:ab3b9860dfa2ca97324abe",
    "measurementId": "G-L456FMG0HB",
    "databaseURL": "https://state-space-controller-design-default-rtdb.firebaseio.com/"
}

firebase = pyrebase.initialize_app(firebaseConfig)

db = firebase.database()

"""
# Pushing initial data to Firebase
initial_names = ["john_doe", "jane_smith", "alex98"]

for name in initial_names:
    db.child("users").child(name).set(True)

"""

"""
# Getting data from Firebase
users = db.child("users").get()

print("🔥 All users in database:")
for user in users.each():
    print(user.key())
"""
"""
students = [
    {"id": "2306254874", "name": "Muhammad Reza"},
]

for student in students:
    db.child("students").child(student["id"]).child(student["name"]).set({
        # you can add other info here if needed
        "status": "active"
    })
"""
db.child("students").child("2306254874").update({
    "problem_set": 9
})

"""
npm = "admin123"
user_data = db.child("students").child(npm).get()
print(user_data.val())


if user_data.val():
            print("User exists! Proceed.")

            # Check if problem_set already exists
            if "problem_set" not in user_data.val():
                print("No problem set yet, assigning one...")
                selected_problem = random.randint(1, 11)
                db.child("students").child(npm).update({
                    "problem_set": selected_problem
                })
                print(f"Assigned problem set {selected_problem}")
            else:
                print(f"User already has problem set: {user_data.val()['problem_set']}")
"""