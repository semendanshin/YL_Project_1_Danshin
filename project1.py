import sys
import sqlite3
from PyQt5 import uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('resources\\main_form.ui', self)
        self.current_user = []
        self.survey_window = Survey(self)
        self.edit_window = Edit(self)
        self.login_window = Login(self)
        self.load_surveys()
        self.pushButton_start.clicked.connect(
            self.survey_window.start_survey)
        self.pushButton_new.clicked.connect(
            self.edit_window.start_edit)
        self.pushButton_start_login.clicked.connect(
            self.login_window.start_login)

    # Загрузка доступных опросов
    def load_surveys(self):
        if self.current_user:
            self.comboBox.clear()
            surveys_list = list(cur.execute(
                """SELECT title FROM surveys
                WHERE deleted=False ORDER BY title"""))
            self.comboBox.addItems([el[0] for el in surveys_list])
            self.pushButton_start.setEnabled(len(surveys_list) > 0)
        else:
            self.comboBox.clear()
            self.comboBox.addItem('Войдите в аккаунт/зарегестрируйтесь')


class Survey(Main, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('resources\\survey_form.ui', self)
        self.parent = parent
        self.pushButton_next.clicked.connect(self.next_question)
        self.pushButton_cancel.clicked.connect(self.end_survey)
        self.pushButton_back.clicked.connect(self.previous_question)
        self.pushButton_back.setEnabled(False)
        self.answers = dict()

    # Открытие окна прохождения опросов
    def start_survey(self):
        # Проверка входа в аккаунт
        if self.parent.current_user:
            # Проверка единоразового прохождения опроса пользоваелем
            if len(list(cur.execute(
                """SELECT answers.id FROM answers
                JOIN questions ON answers.question_id=questions.id
                JOIN surveys ON questions.survey_id=surveys.id
                WHERE surveys.title=? and answers.user_id=?""", (
                    self.parent.comboBox.currentText(),
                    self.parent.current_user[0])))) == 0:
                self.show()
                self.parent.hide()
                self.answers.clear()
                self.setWindowTitle(self.parent.comboBox.currentText())
                self.questions = list(cur.execute(
                    """SELECT questions.id, question
                    FROM questions JOIN surveys
                    ON questions.survey_id=surveys.id
                    WHERE title=?
                    and questions.deleted=False
                    ORDER BY questions.id""", (
                        self.parent.comboBox.currentText(), )))
                self.question_index = -1
                self.next_question()
            else:
                QMessageBox.warning(self, 'Ошибка', (
                    'Невозможно пройти опрос.\n'
                    'Вы уже проходили данный опрос.'))
        else:
            QMessageBox.warning(self, 'Ошибка', (
                'Невозможно пройти опрос.\n'
                'Для начала нужно войти в аккаунт/зарегестрироваться.'))

    # Закрытие окна прохождения опросов
    def end_survey(self):
        self.pushButton_next.setText("Дальше")
        self.lineEdit.setText('')
        self.answers.clear()
        self.parent.show()
        self.hide()

    # Отображение следующего вопроса
    def next_question(self):
        self.write_answer()
        if self.pushButton_next.text() == "Дальше":
            self.question_index += 1
            self.pushButton_back.setEnabled(self.question_index != 0)
            if self.questions[self.question_index][0] in self.answers:
                self.lineEdit.setText(self.answers[
                    self.questions[self.question_index][0]])
            else:
                self.lineEdit.setText("")
            self.label.setText('{}. {}'.format(
                self.question_index + 1,
                self.questions[self.question_index][1]))
            if self.question_index == len(self.questions) - 1:
                self.pushButton_next.setText("Завершить")
            else:
                self.pushButton_next.setText("Дальше")
        else:
            self.save_answers()

    # Отображение предыдущего вопроса
    def previous_question(self):
        self.write_answer()
        if self.question_index > 0:
            self.question_index -= 1
            self.pushButton_back.setEnabled(self.question_index != 0)
            if self.questions[self.question_index][0] in self.answers:
                self.lineEdit.setText(self.answers[
                    self.questions[self.question_index][0]])
            else:
                self.lineEdit.setText("")
            self.label.setText('{}. {}'.format(
                self.question_index + 1,
                self.questions[self.question_index][1]))
            self.pushButton_next.setText("Дальше")

    # Запись ответов в времнный словарь
    def write_answer(self):
        self.answers[self.questions[
            self.question_index][0]] = self.lineEdit.text()

    # Запись ответов в БД
    def save_answers(self):
        for el in self.answers.keys():
            cur.execute("""INSERT INTO answers
                (question_id, user_id, answer) VALUES (?, ?, ?)""", (
                el, self.parent.current_user[0], self.answers[el]))
        con.commit()
        QMessageBox.information(self, 'Прохождение опроса', (
            'Опрос пройден успешно.\n'
            'Ваши ответы были записаны.'))
        self.end_survey()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.next_question()
        elif event.key() == Qt.Key_Right:
            self.next_question()
        elif event.key() == Qt.Key_Left:
            self.previous_question()


class Edit(Main, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('resources\\edit_form.ui', self)
        self.parent = parent
        self.current_survey = []
        self.pushButton_cancel.clicked.connect(self.end_edit)
        self.pushButton_minus.clicked.connect(self.delete_question_from_table)
        self.pushButton_plus.clicked.connect(self.add_question_to_table)
        self.pushButton_save.clicked.connect(self.save_survey)
        self.pushButton_delete.clicked.connect(self.delete_survey)
        self.comboBox.currentTextChanged.connect(self.display_survey)
        self.comboBox.highlighted.connect(self.check_for_changes)
        self.lineEdit_2.textChanged.connect(self.survey_changed)
        self.lineEdit.textChanged.connect(self.survey_changed)
        self.tableWidget.itemChanged.connect(self.survey_changed)

    # Открытие окна редактирования опросов
    def start_edit(self):
        if self.parent.current_user:
            self.comboBox.blockSignals(False)
            self.comboBox.addItems(['Создать новый'] + [
                el[0] for el in list(cur.execute(
                    """SELECT title FROM surveys
                        WHERE deleted=False and creator_id=?""", (
                        self.parent.current_user[0], )).fetchall())])
            self.pushButton_save.setEnabled(False)
            self.changed = False
            self.show()
            self.parent.hide()
            self.display_survey()
        else:
            QMessageBox.warning(self, 'Ошибка', (
                'Невозможно вносить изменения в опросы.\n'
                'Для начала нужно войти в аккаунт/зарегестрироваться.'))

    # Закрытие окна редактирования опросов
    def end_edit(self):
        if self.check_for_changes():
            self.comboBox.blockSignals(True)
            self.current_survey = []
            self.comboBox.clear()
            self.parent.load_surveys()
            self.parent.show()
            self.hide()

    # Отоюражение даных об опросе
    def display_survey(self):
        self.lineEdit.blockSignals(True)
        self.lineEdit_2.blockSignals(True)
        self.tableWidget.blockSignals(True)
        if self.comboBox.currentText() != 'Создать новый':
            self.current_survey = list(cur.execute("""SELECT id, title,
                description FROM surveys WHERE title=?
                and deleted=False""", (self.comboBox.currentText(), )))[0]
            self.lineEdit.setText(self.current_survey[1])
            self.lineEdit_2.setText(self.current_survey[2])
        else:
            self.current_survey = []
            self.lineEdit.setText('')
            self.lineEdit_2.setText('')
        self.display_questions()
        self.changed = False
        self.pushButton_save.setEnabled(False)
        self.lineEdit.blockSignals(False)
        self.lineEdit_2.blockSignals(False)
        self.tableWidget.blockSignals(False)

    # Отображение вопросов в таблице
    def display_questions(self):
        if self.current_survey:
            current_questions = list(cur.execute("""SELECT question
                FROM questions WHERE survey_id=? and deleted=False
                ORDER BY id""", (str(self.current_survey[0]), )))
            if current_questions:
                self.tableWidget.setColumnCount(1)
                self.tableWidget.setHorizontalHeaderLabels(
                    ['Формулировка вопроса'])
                self.tableWidget.setRowCount(len(current_questions))
                for i, el in enumerate(current_questions):
                    for j, val in enumerate(el):
                        self.tableWidget.setItem(
                            i, j, QTableWidgetItem(str(val)))
                        self.tableWidget.resizeColumnToContents(0)
        else:
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)

    # Добавление вопроса в таблицу
    def add_question_to_table(self):
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setHorizontalHeaderLabels(
            ['Формулировка вопроса'])
        i = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(i + 1)
        self.tableWidget.setItem(i, 0, QTableWidgetItem(''))
        self.survey_changed()

    # Удаление вопроса из таблицы
    def delete_question_from_table(self):
        item = self.tableWidget.selectedItems()
        if item:
            self.tableWidget.removeRow(item[0].row())
            self.tableWidget.resizeColumnToContents(0)
            self.survey_changed()

    # Сохранение опросов
    def save_survey(self):
        # Проверка наличия названия опроса и, хотя бы одного вопроса
        if self.tableWidget.rowCount() > 0 and self.lineEdit.text() != '':
            # Проверка на уникальность названия опроса при создании нового
            if self.check_for_unique_title():
                # Удаление старых записей об опросе,
                # если редактируется существующий опрос
                if self.comboBox.currentText() != 'Создать новый':
                    self.delete_records_about_survey()
                # Запись данных об опросе
                cur.execute("""INSERT INTO surveys
                    (title, description, creator_id) VALUES
                    (?, ?, ?)""", (
                            self.lineEdit.text(),
                            self.lineEdit_2.text(),
                            self.parent.current_user[0]))
                self.current_survey = list(cur.execute("""SELECT id, title,
                    description FROM surveys WHERE title=? and
                    deleted=False""", (self.lineEdit.text(), )))[0]
                # Сохранение вопросов
                for i in range(self.tableWidget.rowCount()):
                    question_text = self.tableWidget.item(i, 0).text()
                    cur.execute("""INSERT INTO questions
                        (survey_id, question) VALUES (?, ?)""", (
                        str(self.current_survey[0]), question_text))
                con.commit()
                self.comboBox.addItem(self.current_survey[1])
                self.comboBox.setCurrentText(self.current_survey[1])
                return True
            else:
                self.raise_edit_warning_message(
                    'Опрос с таким названием уже существует.')
        else:
            self.raise_edit_warning_message(
                'У каждого опроса должно быть уникальное '
                'название и, как минимум, один вопрос.')

    def raise_edit_warning_message(self, text):
        QMessageBox.warning(
            self, 'Ошибка', 'Невозможно сохранить опрос.\n' + text)

    # Удаление опросов из базы данных
    def delete_survey(self):
        if self.comboBox.currentText() != 'Создать новый':
            self.delete_records_about_survey()
            con.commit()
            self.comboBox.setCurrentText("Создать новый")
        self.display_survey()

    def delete_records_about_survey(self):
        cur.execute("""UPDATE surveys SET deleted=True
                        WHERE id=?""", (str(self.current_survey[0]), ))
        cur.execute("""UPDATE questions SET deleted=True
            WHERE survey_id=?""", (str(self.current_survey[0]), ))
        self.comboBox.blockSignals(True)
        self.comboBox.removeItem(self.comboBox.currentIndex())
        self.comboBox.blockSignals(False)
        self.changed = False

    def survey_changed(self):
        self.tableWidget.resizeColumnToContents(0)
        self.pushButton_save.setEnabled(True)
        self.changed = True

    def ask_about_save(self):
        msg = QMessageBox()
        msg.setWindowTitle('Внимание')
        msg.setText('В этом опросе присутствуют несохраненные изменения.\n'
                    'Хотите их сохранить?')
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Ok | (
            QMessageBox.Cancel) | QMessageBox.Discard)
        msg.button(QMessageBox.Ok).setText('Да')
        msg.button(QMessageBox.Cancel).setText('Отмена')
        msg.button(QMessageBox.Discard).setText('Нет')
        msg.setWindowIcon(QtGui.QIcon('resources\\project1logo.ico'))
        return msg.exec()

    def check_for_changes(self):
        if self.changed:
            result = self.ask_about_save()
            if result == QMessageBox.Ok:
                if self.save_survey():
                    return True
            elif result == QMessageBox.Discard:
                self.pushButton_save.setEnabled(False)
                self.changed = False
                return True
            elif result == QMessageBox.Cancel:
                return False
        else:
            return True

    def check_for_unique_title(self):
        return self.comboBox.currentText() != 'Создать новый' or (
            self.lineEdit.text() not in [el[0] for el in list(
                cur.execute("""SELECT title FROM surveys
                WHERE deleted=False"""))] and (
                self.lineEdit.text() != 'Создать новый'))


# Форма, реализующая вход в аккаунт
class Login(Main, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('resources\\login_form.ui', self)
        self.parent = parent
        self.register_window = Register(self)
        self.pushButton_cancel.clicked.connect(self.end_login)
        self.pushButton_start_register.clicked.connect(
            self.register_window.start_register)
        self.pushButton_login.clicked.connect(self.login)

    # Открытие окна входа
    def start_login(self):
        self.show()
        self.parent.hide()

    # Закрытие окна входа
    def end_login(self):
        self.parent.load_surveys()
        self.parent.show()
        self.hide()
        self.lineEdit_login.setText('')

    # Вход в аккаунт
    def login(self):
        # Проверка на пустые поля
        if len(self.lineEdit_login.text()) > 0 and (
                len(self.lineEdit_password.text()) > 0):
            # Проверка на правильность логина
            if self.lineEdit_login.text() in [el[0] for el in list(
                cur.execute("""SELECT login FROM users
                    WHERE deleted=False"""))]:
                # Проверка на правильность пароля
                if self.lineEdit_password.text() == list(
                    cur.execute("""SELECT password FROM users
                    WHERE login=? and deleted=False""", (
                        self.lineEdit_login.text(), )))[0][0]:
                    self.parent.current_user = list(cur.execute("""SELECT
                    id, first_name, second_name FROM users WHERE login=?""", (
                        self.lineEdit_login.text(), )))[0]
                    self.parent.pushButton_start_login.setText('Выйти')
                    self.parent.pushButton_start_login.disconnect()
                    self.parent.pushButton_start_login.clicked.connect(
                        self.logout)
                    self.parent.label_name.setText(
                        'Здравствуйте, {} {}'.format(
                            self.parent.current_user[1],
                            self.parent.current_user[2]))
                    self.end_login()
                else:
                    self.raise_login_warning_message(
                        'Неверный пароль.')
            else:
                self.raise_login_warning_message(
                    'Такого логина не существует.')
        else:
            self.raise_login_warning_message(
                'Одно или несколько из обязательных полей пустое.')
        self.lineEdit_password.setText('')

    def raise_login_warning_message(self, text):
        QMessageBox.warning(self, 'Ошибка', 'Вход не выполнен.\n' + text)

    # Выход из текущего аккаунта
    def logout(self):
        self.parent.current_user = []
        self.parent.pushButton_start_login.disconnect()
        self.parent.pushButton_start_login.clicked.connect(self.start_login)
        self.parent.pushButton_start_login.setText('Вход/Регистрация')
        self.parent.load_surveys()
        self.parent.label_name.setText('')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.login()


# Форма, реализующая регистрацию пользователей
class Register(Login, QMainWindow):
    def __init__(self, parent):
        super(QMainWindow, self).__init__()
        uic.loadUi('resources\\register_form.ui', self)
        self.parent = parent
        self.pushButton_register.clicked.connect(self.register)
        self.pushButton_cancel.clicked.connect(self.end_register)

    # Открытие окна регистрации
    def start_register(self):
        self.show()
        self.parent.hide()

    # Закрытие окна регистрации
    def end_register(self):
        self.hide()
        self.lineEdit_login.setText('')
        self.lineEdit_password.setText('')
        self.lineEdit_password2.setText('')
        self.lineEdit_firstname.setText('')
        self.lineEdit_secondname.setText('')
        self.spinBox.setValue(0)
        self.comboBox.setCurrentText('Мужской')
        self.parent.show()

    # Регистрация
    def register(self):
        # Проверка на пустые поля
        if self.lineEdit_login.text() != '' and (
                self.lineEdit_password.text()) != '' and (
                self.lineEdit_password2.text()) != '' and (
                self.lineEdit_firstname.text()) != '' and (
                self.lineEdit_secondname.text()) != '':
            # Проверка на уникальность логина
            if self.lineEdit_login.text() not in [el[0] for el in list(
                cur.execute("""SELECT login FROM users
                    WHERE deleted=False"""))]:
                # Проверка пароля
                if self.lineEdit_password.text() == (
                        self.lineEdit_password2.text()):
                    sex = 1 if self.comboBox.currentText() == 'Мужской' else 0
                    cur.execute("""INSERT INTO users (login, password,
                        first_name, second_name, age, sex) VALUES
                        (?, ?, ?, ?, ?, ?)""", (
                                self.lineEdit_login.text(),
                                self.lineEdit_password.text(),
                                self.lineEdit_firstname.text(),
                                self.lineEdit_secondname.text(),
                                self.spinBox.value(),
                                sex))
                    con.commit()
                    QMessageBox.information(self, 'Регистрация', (
                        'Регистрация пройдена успешно.'))
                    self.end_register()
                else:
                    self.raise_register_warning_message(
                        'Пароли не совпадают.')
            else:
                self.raise_register_warning_message(
                    'Такой логин уже существует.')
        else:
            self.raise_register_warning_message(
                'Необходимо заполнить все поля.')

    def raise_register_warning_message(self, text):
        QMessageBox.warning(
            self, 'Ошибка', 'Регистрация не выполнена.\n' + text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.register()


if __name__ == '__main__':
    con = sqlite3.connect('resources\\survey_db.sqlite')
    cur = con.cursor()
    app = QApplication(sys.argv)
    worker = Main()
    worker.show()
    sys.exit(app.exec())
