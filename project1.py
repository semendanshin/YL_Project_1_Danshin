import sys
import sqlite3
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
# Сделать аккаунты; Добавить автосохранение во вкладке edit; css оформление; Добавить обязательные вопросы; Экспорт; Сделать иконку


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_form.ui', self)
        self.show()
        self.curent_user = []
        self.survey_window = Survey(self)
        self.edit_window = Edit(self)
        self.login_window = Login(self)
        self.pushButton_start.clicked.connect(
            self.survey_window.start_survey)
        self.pushButton_new.clicked.connect(
            self.edit_window.start_edit)
        self.pushButton_login.clicked.connect(
            self.login_window.start_login)

    def load_surveys(self):
        if self.curent_user:
            self.surveys = list(cur.execute(
                """SELECT id, title FROM surveys
                WHERE deleted=False and creator_id=? ORDER BY title""", (
                    str(self.curent_user[0]))))
            self.comboBox.addItems([el[1] for el in self.surveys])
            self.pushButton_start.setEnabled(len(self.surveys) != 0)


class Survey(Main, QMainWindow):
    def __init__(self, parent):
        self.parent = parent
        super(QMainWindow, self).__init__()
        uic.loadUi('survey_form.ui', self)
        self.pushButton_next.clicked.connect(self.next_question)
        self.pushButton_cancel.clicked.connect(self.end_survey)
        self.pushButton_back.clicked.connect(self.previous_question)
        self.pushButton_back.setEnabled(False)
        self.label.setWordWrap(True)
        self.answers = dict()

    def next_question(self):
        self.write_answer()
        if self.question_index < len(self.questions) - 1:
            self.question_index += 1
            self.pushButton_back.setEnabled(self.question_index != 0)
            if self.questions[self.question_index][0] in self.answers:
                answer = self.answers[
                    self.questions[self.question_index][0]][1]
                self.lineEdit.setText(answer)
            else:
                self.lineEdit.setText("")
            text = '{}. ' + self.questions[self.question_index][2]
            self.label.setText(text.format(self.question_index + 1))
            if self.question_index == len(self.questions) - 1:
                self.pushButton_next.setText("Завершить")
            else:
                self.pushButton_next.setText("Дальше")
        else:
            self.save_answers()

    def previous_question(self):
        self.write_answer()
        self.question_index -= 1
        self.pushButton_back.setEnabled(self.question_index != 0)
        if self.questions[self.question_index][0] in self.answers:
            answer = self.answers[
                self.questions[self.question_index][0]][1]
            self.lineEdit.setText(answer)
        else:
            self.lineEdit.setText("")
        text = '{}. ' + self.questions[self.question_index][2]
        self.label.setText(text.format(self.question_index + 1))
        self.pushButton_next.setText("Дальше")

    def write_answer(self):
        self.answers[self.questions[self.question_index][0]] = (
            1, self.lineEdit.text())

    def save_answers(self):
        for el in self.answers.keys():
            cur.execute("""INSERT INTO answers
                (question_id, user_id, answer) VALUES (?, ?, ?)""", (
                el, self.answers[el][0], self.answers[el][1]))
        con.commit()
        self.answers.clear()
        self.end_survey()

    def start_survey(self):
        self.parent.setEnabled(False)
        self.show()
        title = self.parent.comboBox.currentText()
        self.setWindowTitle(title)
        request = f"""SELECT questions.id, surveys.id, question
            FROM questions JOIN surveys
            ON questions.survey_id=surveys.id
            WHERE title='{title}'
            and questions.deleted=False
            ORDER BY questions.id"""
        self.questions = list(cur.execute(request))
        self.question_index = -1
        self.next_question()

    def end_survey(self):
        self.hide()
        self.parent.setEnabled(True)


class Edit(Main, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('edit_form.ui', self)
        self.parent = parent
        self.changed = False
        self.current_survey = []
        self.pushButton_save.setEnabled(False)
        self.comboBox.currentTextChanged.connect(self.display_survey)
        self.comboBox.highlighted.connect(self.check_for_changes)
        self.pushButton_cancel.clicked.connect(self.end_edit)
        self.pushButton_minus.clicked.connect(self.delete_question)
        self.pushButton_plus.clicked.connect(self.add_question)
        self.pushButton_save.clicked.connect(self.save_survey)
        self.pushButton_delete.clicked.connect(self.delete_survey)
        self.lineEdit_2.textChanged.connect(self.survey_changed)
        self.lineEdit.textChanged.connect(self.survey_changed)
        self.tableWidget.itemChanged.connect(self.survey_changed)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setHorizontalHeaderLabels(
            ['Формулировка вопроса'])
        self.tableWidget.resizeColumnToContents(0)

    def start_edit(self):
        self.comboBox.clear()
        self.comboBox.addItems([el[0] for el in self.parent.surveys])
        self.parent.setEnabled(False)
        self.show()
        self.display_survey()

    def end_edit(self):
        self.comboBox.setCurrentText("Создать новый")
        self.current_survey.clear()
        self.hide()
        self.parent.load_surveys()
        self.parent.setEnabled(True)

    def display_survey(self):
        if self.comboBox.currentText() == 'Создать новый':
            self.pushButton_delete.setEnabled(False)
            self.current_survey = []
            self.current_questions = []
            self.lineEdit.setText('')
            self.lineEdit_2.setText('')
        else:
            self.current_survey = list(cur.execute("""SELECT id, title,
                description FROM surveys WHERE title=?
                and deleted=False""", (self.comboBox.currentText(), )))[0]
            self.pushButton_delete.setEnabled(True)
            self.lineEdit.setText(self.current_survey[1])
            self.lineEdit_2.setText(self.current_survey[2])
        self.display_questions()

    def display_questions(self):
        if self.current_survey:
            self.current_questions = list(cur.execute("""SELECT question
                FROM questions WHERE survey_id=? and deleted=False
                ORDER BY id""", (str(self.current_survey[0]), )))
            if self.current_questions:
                self.tableWidget.setRowCount(len(self.current_questions))
                for i, el in enumerate(self.current_questions):
                    for j, val in enumerate(el):
                        self.tableWidget.setItem(
                            i, j, QTableWidgetItem(str(val)))
                        self.tableWidget.resizeColumnToContents(0)
        else:
            self.tableWidget.setRowCount(0)
        self.pushButton_save.setEnabled(False)
        self.changed = False

    def add_question(self):
        i = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(i + 1)
        self.tableWidget.setItem(i, 0, QTableWidgetItem(''))
        self.tableWidget.resizeColumnToContents(0)
        self.survey_changed()

    def delete_question(self):
        item = self.tableWidget.selectedItems()
        if item:
            self.tableWidget.removeRow(item[0].row())
            self.tableWidget.resizeColumnToContents(0)
            self.survey_changed()

    def save_survey(self):
        if self.tableWidget.rowCount() > 0 and self.lineEdit.text() != '':
            surveys = list(cur.execute("""SELECT title FROM surveys
            WHERE deleted=False"""))
            surveys = [el[0] for el in surveys]
            if self.comboBox.currentText() != 'Создать новый' or self.lineEdit.text() not in surveys:
                if self.comboBox.currentText() != 'Создать новый':
                    cur.execute("""UPDATE surveys SET deleted=True
                        WHERE id=?""", (str(self.current_survey[0]), ))
                    cur.execute("""UPDATE questions SET deleted=True
                        WHERE survey_id=?""", (str(self.current_survey[0]), ))

                cur.execute("""INSERT INTO surveys (title, description) VALUES
                    (?, ?)""", (self.lineEdit.text(), self.lineEdit_2.text()))

                self.current_survey = list(cur.execute("""SELECT id, title,
                    description FROM surveys WHERE title=? and
                    deleted=False""", (self.lineEdit.text(), )))[0]

                for i in range(self.tableWidget.rowCount()):
                    question_text = self.tableWidget.item(i, 0).text()
                    cur.execute("""INSERT INTO questions
                        (survey_id, question) VALUES (?, ?)""", (
                        str(self.current_survey[0]), question_text))
                con.commit()

                self.comboBox.addItem(self.current_survey[1])
                if self.comboBox.currentText() != 'Создать новый':
                    self.comboBox.removeItem(self.comboBox.currentIndex())
                self.comboBox.setCurrentText(self.current_survey[1])
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Ошибка')
                msg.setText('Невозможно сохранить опрос.')
                msg.setInformativeText(
                    'Опрос с таким названием уже существует.')
                msg.exec()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Ошибка')
            msg.setText('Невозможно сохранить опрос.')
            msg.setInformativeText(
                'У каждого опроса должно быть уникальное '
                'название и, как минимум, один вопрос.')
            msg.exec()

    def delete_survey(self):
        if self.comboBox.currentText() != 'Создать новый':
            survey_template = """UPDATE surveys SET deleted=True
            WHERE id=? and deleted=False"""
            questions_template = """UPDATE questions
                SET deleted=True WHERE survey_id=?
                and deleted=False"""
            cur.execute(survey_template, (str(self.current_survey[0]), ))
            cur.execute(questions_template, (str(self.current_survey[0]), ))
            con.commit()
            self.comboBox.removeItem(self.comboBox.currentIndex())
        self.comboBox.setCurrentText("Создать новый")

    def survey_changed(self):
        self.tableWidget.resizeColumnToContents(0)
        self.pushButton_save.setEnabled(True)
        self.changed = True

    def check_for_changes(self):
        pass


class Login(Main, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('login_form.ui', self)
        self.parent = parent
        self.pushButton_cancel.clicked.connect(self.end_login)
        self.pushButton_register.clicked.connect(self.register)
        self.pushButton_login.clicked.connect(self.login)

    def start_login(self):
        self.show()
        self.parent.setEnabled(False)

    def end_login(self):
        self.hide()
        self.lineEdit_login.setText('')
        self.lineEdit_password.setText('')
        self.parent.setEnabled(True)

    def login(self):
        if len(self.lineEdit_login.text()) > 0 and len(self.lineEdit_password.text()) > 0:
            logins = [el[0] for el in list(cur.execute("""SELECT login
                FROM users WHERE deleted=False"""))]
            if self.lineEdit_login.text() in logins:
                password = list(cur.execute("""SELECT password FROM users
                    WHERE login=? and deleted=False""", (
                    self.lineEdit_login.text(), )))[0][0]
                if self.lineEdit_password.text() == password:
                    self.parent.curent_user = list(cur.execute("""SELECT
                    id, first_name, second_name FROM users WHERE login=?""", (
                        self.lineEdit_login.text(), )))[0]
                else:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle('Ошибка')
                    msg.setText('Вход не выполнен.')
                    msg.setInformativeText('Неверный пароль.')
                    msg.exec()
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Ошибка')
                msg.setText('Вход не выполнен.')
                msg.setInformativeText('Неверный логин.')
                msg.exec()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Ошибка')
            msg.setText('Вход не выполнен.')
            msg.setInformativeText(
                'Одное или несколько из обязательных полей пустое.')
            msg.exec()

    def register(self):
        pass


if __name__ == '__main__':
    con = sqlite3.connect('survey_db.sqlite')
    cur = con.cursor()
    app = QApplication(sys.argv)
    worker = Main()
    sys.exit(app.exec())
