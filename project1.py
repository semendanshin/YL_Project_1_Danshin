import sys
import sqlite3
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
# Сделать аккаунты; Добавить автосохранение во вкладке edit; Проверка на пустые поля в edit; css оформление


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_form.ui', self)
        self.show()
        self.load_surveys()
        self.survey_window = Survey(self)
        self.edit_window = Edit(self)
        self.pushButton_start.clicked.connect(
            self.survey_window.start_survey)
        self.pushButton_new.clicked.connect(
            self.edit_window.start_edit)

    def load_surveys(self):
        self.surveys = list(cur.execute(
            """SELECT id, title FROM surveys
            WHERE deleted=False ORDER BY title"""))
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

    def previous_question(self):
        self.write_answer()
        if self.question_index > 0:
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

    def next_question(self):
        self.write_answer()
        if self.question_index < len(self.questions) - 1:
            self.question_index += 1
            self.pushButton_back.setEnabled(True)
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

    def write_answer(self):
        self.answers[self.questions[self.question_index][0]] = (
            1, self.lineEdit.text())

    def save_answers(self):
        answer_template = """INSERT INTO answers (question_id, user_id, answer)
                VALUES (?, ?, ?)"""
        for el in self.answers.keys():
            cur.execute(answer_template,
                        (el, self.answers[el][0], self.answers[el][1]))
        self.answers = dict()
        con.commit()
        self.end_survey()

    def start_survey(self):
        self.parent.hide()
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
        self.parent.show()


class Edit(Main, QMainWindow):
    def __init__(self, parent):
        self.parent = parent
        super(QMainWindow, self).__init__()
        uic.loadUi('edit_form.ui', self)
        self.changed = False
        self.current_survey = []
        self.pushButton_save.setEnabled(False)
        self.lineEdit_2.textChanged.connect(self.survey_changed)
        self.lineEdit.textChanged.connect(self.survey_changed)
        self.comboBox.addItems([el[1] for el in parent.surveys])
        self.comboBox.currentTextChanged.connect(self.display_survey)
        self.pushButton_cancel.clicked.connect(self.end_edit)
        self.pushButton_minus.clicked.connect(self.delete_question)
        self.pushButton_plus.clicked.connect(self.add_question)
        self.pushButton_save.clicked.connect(self.save_survey)
        self.pushButton_delete.clicked.connect(self.delete_survey)
        self.tableWidget.itemChanged.connect(self.survey_changed)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setHorizontalHeaderLabels(
            ['Формулировка вопроса'])
        self.tableWidget.resizeColumnToContents(0)

    def survey_changed(self):
        self.pushButton_save.setEnabled(True)
        self.changed = True

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

    def add_question(self):
        i = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(i + 1)
        self.tableWidget.setItem(i, 0, QTableWidgetItem(''))
        self.tableWidget.resizeColumnToContents(0)

    def delete_question(self):
        item = self.tableWidget.selectedItems()
        if item:
            self.tableWidget.removeRow(item[0].row())
            self.tableWidget.resizeColumnToContents(0)

    def save_survey(self):
        if self.survey_changed:
            question_template = """INSERT INTO questions
                    (survey_id, question) VALUES (?, ?)"""

            if self.comboBox.currentText() == 'Создать новый':
                survey_template = """INSERT INTO surveys
                    (title, description) VALUES (?, ?)"""
                cur.execute(survey_template,
                            (self.lineEdit.text(), self.lineEdit_2.text()))
            else:
                survey_template = """UPDATE surveys
                    SET (title, description) = (?, ?)
                    WHERE id=?"""
                cur.execute(survey_template,
                            (self.lineEdit.text(),
                                self.lineEdit_2.text(),
                                str(self.current_survey[0])))

            self.current_survey = list(cur.execute("""SELECT id, title,
                description FROM surveys
                WHERE title=? and
                deleted=False""", (self.lineEdit.text(), )))[0]
            cur.execute("""UPDATE questions SET deleted=True
                WHERE survey_id=?""", (str(self.current_survey[0]), ))

            for i in range(self.tableWidget.rowCount()):
                question_text = self.tableWidget.item(i, 0).text()
                cur.execute(question_template, (
                    str(self.current_survey[0]), question_text))

            self.comboBox.addItem(self.lineEdit.text())
            self.comboBox.setCurrentText(self.lineEdit.text())
            self.pushButton_save.setEnabled(False)
            self.changed = False
            con.commit()

    def display_survey(self):
        if self.comboBox.currentText() == 'Создать новый':
            self.pushButton_delete.setEnabled(False)
            self.current_survey = []
            self.lineEdit.setText('')
            self.lineEdit_2.setText('')
            self.display_questions()
        else:
            self.pushButton_delete.setEnabled(True)
            self.current_survey = list(cur.execute("""SELECT id, title,
                description FROM surveys WHERE title=?
                and deleted=False""", (self.comboBox.currentText(), )))[0]
            self.lineEdit.setText(self.current_survey[1])
            self.lineEdit_2.setText(self.current_survey[2])
            self.display_questions()
        self.pushButton_save.setEnabled(False)
        self.changed = False

    def display_questions(self):
        if self.current_survey:
            self.current_questions = list(cur.execute("""SELECT question
                FROM questions WHERE survey_id=? and deleted=False
                ORDER BY id""", (str(self.current_survey[0]), )))
            print(self.current_questions)
            if self.current_questions:
                self.tableWidget.setRowCount(len(self.current_questions))
                for i, el in enumerate(self.current_questions):
                    for j, val in enumerate(el):
                        print(val)
                        self.tableWidget.setItem(
                            i, j, QTableWidgetItem(str(val)))
                        self.tableWidget.resizeColumnToContents(0)
        else:
            self.current_questions = []
            self.tableWidget.setRowCount(0)

    def start_edit(self):
        self.show()
        self.parent.hide()

    def end_edit(self):
        self.comboBox.setCurrentText("Создать новый")
        self.current_survey = []
        self.hide()
        self.parent.load_surveys()
        self.parent.show()


if __name__ == '__main__':
    con = sqlite3.connect('survey_db.sqlite')
    cur = con.cursor()
    app = QApplication(sys.argv)
    worker = Main()
    sys.exit(app.exec())
