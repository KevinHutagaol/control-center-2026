class UserContext:
    def __init__(self):
        self.email = None
        self.uid = None
        self.display_name = None
        self.student_id = None
        self.group = None
        self.regOrKKi = None
        self.year = None
        self.role = None
        self.is_logged_in = False

    def set_user(self, email, uid, display_name, student_id, group, regOrKKi, year, role):
        self.email = email
        self.uid = uid
        self.display_name = display_name
        self.student_id = student_id
        self.group = group
        self.regOrKKi = regOrKKi
        self.year = year
        self.role = role
        self.is_logged_in = True

    def clear(self):
        self.email = None
        self.uid = None
        self.display_name = None
        self.student_id = None
        self.group = None
        self.regOrKKi = None
        self.year = None
        self.role = None
        self.is_logged_in = False

user_context = UserContext()