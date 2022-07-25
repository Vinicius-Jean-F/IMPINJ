import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QTimer, QRegExp, QPoint,
                          QAbstractTableModel)
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QToolTip, QLabel, QLineEdit, QComboBox, QCheckBox, \
    QTableWidget, QTableWidgetItem, QVBoxLayout, QSlider

from threading import Thread
import csv
import os.path
import time
from datetime import datetime
from sllurp import llrp
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT
from datetime import datetime

HISTERESIS_DRINKING_TIME = 10

GUI_APP_TITLE = 'Hello World IMPINJ Reader'

DEFAULT_ANTENNA_LIST = [1, 2]
DEFAULT_POWER_TABLE = [index for index in range(15, 25, 1)]

list_1 = []
list_intern_table = []

factory_args = dict(
    duration=10,
    report_every_n_tags=1,
    antennas=(DEFAULT_ANTENNA_LIST[0],),
    tx_power={DEFAULT_ANTENNA_LIST[0]: 0},
    mode_identifier=2,
    tag_population=1,
    tari=0,
    session=2,
    start_inventory=True,
    tag_content_selector={
        "EnableROSpecID": False,
        "EnableSpecIndex": False,
        "EnableInventoryParameterSpecID": False,
        "EnableAntennaID": False,
        "EnableChannelIndex": False,
        "EnablePeakRSSI": False,
        "EnableFirstSeenTimestamp": True,
        "EnableLastSeenTimestamp": True,
        "EnableTagSeenCount": False,
        "EnableAccessSpecID": False,
    },
    event_selector={
        'HoppingEvent': False,
        'GPIEvent': False,
        'ROSpecEvent': True,
        'ReportBufferFillWarning': True,
        'ReaderExceptionEvent': True,
        'RFSurveyEvent': False,
        'AISpecEvent': True,
        'AISpecEventWithSingulation': False,
        'AntennaEvent': False,
    },
    search_mode=2,
)


####################################################################
######################MAIN THREAD OF THE CODE#######################
####################################################################
class Th(Thread):
    def __init__(self, num):
        Thread.__init__(self)

    def run(self):
        while True:
            time_now = datetime.utcnow()

            for x in range(len(list_1)):
                tag_timeout = time_now - list_1[x]['LastSeenTimestampUTC']
                # print(tag_timeout.total_seconds())
                if (tag_timeout.total_seconds() > (HISTERESIS_DRINKING_TIME - 11.5)):
                    print("Tag %s has left" % (list_1[x]['EPC']))
                    write_csv(list_1[x])  # write the line to CSV
                    list_intern_table.append(list_1[x])
                    del list_1[x]
                    break;


####################################################################
###########FUNCTION TO WRITE A NEW LINE TO THE CSV FILE#############
####################################################################
def write_csv(line):
    if os.path.isfile('sample.csv'):
        # print('file already exists')
        with open('sample.csv', 'a', newline='') as f:
            field_names = dict.keys(line)
            writer = csv.DictWriter(f, fieldnames=field_names)
            data = dict(line)
            writer.writerow(data)
            f.close()
    else:
        # print('file does not exist, creating...')
        with open('sample.csv', 'w', newline='') as f:
            field_names = dict.keys(line)
            writer = csv.writer(f)
            writer.writerow(field_names)
            writer = csv.DictWriter(f, fieldnames=field_names)
            data = dict(line)
            writer.writerow(data)
            f.close()


class Gui(QObject):

    def __init__(self):
        super(Gui, self).__init__()
        # variables
        self.LLRP_DEFAULT_HOST = ''  # 169.254.1.1
        self.LLRP_DEFAULT_PORT = 5084
        self.reader = None

    def connect(self):
        config = LLRPReaderConfig(factory_args)
        self.reader = LLRPReaderClient(self.LLRP_DEFAULT_HOST, self.LLRP_DEFAULT_PORT, config)
        self.reader.add_tag_report_callback(self.tag_report_cb)

        connected = self.reader.is_alive()

        if connected:
            print('READER ALREADY CONNECTED')
            return 2
        else:
            try:
                self.reader.connect()
                return 0
            except:
                return 1

    def disconnect(self):
        """close connection with the reader
        """
        if self.reader is not None:
            self.reader.join(0.1)
            try:
                self.reader.disconnect()
                self.reader.join(0.1)
            except Exception:
                pass

    def update_cfg(self):
        self.disconnect()
        self.connect()

    def connection_status(self):
        if self.reader is not None:
            if self.reader.is_alive():
                status = 0
            else:
                status = 1
        else:
            status = 1

        return status

    ####################################################################
    ########FUNCTION TO MANAGE NEW ENTRIES IN THE DRINKING SPOT#########
    ####################################################################

    def tag_report_cb(self, reader, tag_reports):
        for tag in tag_reports:
            full_dictionary = tag
            LastTime = datetime.fromtimestamp((full_dictionary['LastSeenTimestampUTC'] / 1000000))
            FirstTime = datetime.fromtimestamp((full_dictionary['FirstSeenTimestampUTC'] / 1000000))
            full_dictionary.update({'LastSeenTimestampUTC': LastTime})
            full_dictionary.update({'FirstSeenTimestampUTC': FirstTime})

            EPC = full_dictionary['EPC']
            if (len(list_1) == 0):
                list_1.append(full_dictionary)
                print("Tag %s is drinking" % full_dictionary['EPC'])
            else:
                for i in range(len(list_1)):
                    dic_aux = list_1[i]
                    if (EPC == dic_aux['EPC']):
                        list_1[i].update({'LastSeenTimestampUTC': LastTime})
                        break;
                    if (i >= (len(list_1) - 1)):
                        list_1.append(full_dictionary)
                        print("Tag %s is drinking" % (full_dictionary['EPC']))


####################################################################
##################CODE FOR OPEN THE MAIN WINDOW#####################
####################################################################
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.topo = 100
        self.esquerda = 100
        self.largura = 1200
        self.altura = 600
        self.titulo = GUI_APP_TITLE
        self.reader_connected = False

        self.IMPINJ = Gui()

        self.internal_list_size = len(list_intern_table)
        self.connection_state = 1

        ###########################################
        #################TEXT BOX##################
        ###########################################

        # IP INPUT TEXT BOX

        self.host_box = QLineEdit(self)
        self.host_box.setAlignment(QtCore.Qt.AlignCenter)
        self.host_box.move(50, 40)
        self.host_box.resize(200, 40)
        self.host_box.setStyleSheet('QLineEdit {font:bold; font-size: 24px}')
        self.host_box.setText('169.254.1.1')

        # PORT INPUT TEXT BOX

        self.port_box = QLineEdit(self)
        self.port_box.setAlignment(QtCore.Qt.AlignCenter)
        self.port_box.move(350, 40)
        self.port_box.resize(120, 40)
        self.port_box.setStyleSheet('QLineEdit {font:bold; font-size: 24px}')
        self.port_box.setText('5084')

        ###########################################
        ###############CRIAR BOTAO#################
        ###########################################

        self.botao1 = QPushButton('Connect', self)
        self.botao1.move(10, 120)
        self.botao1.resize(175, 50)
        self.botao1.setStyleSheet('QPushButton {background-color:#0FB328; font:bold; font-size: 24px}')
        self.botao1.clicked.connect(self.botao1_click)

        self.botao2 = QPushButton('Update Config', self)
        self.botao2.move(10, 540)
        self.botao2.resize(200, 50)
        self.botao2.setStyleSheet('QPushButton {background-color:blue; font:bold; font-size: 24px}')
        self.botao2.clicked.connect(self.botao2_click)

        # LABEL FOR THE STATUS OF THE CONNECTION

        self.label_1 = QLabel(self)
        self.label_1.setText("Disconnected")
        self.label_1.move(10, 90)
        self.label_1.resize(500, 25)
        self.label_1.setStyleSheet('QLabel {font:bold; font-size:24px; color:"red"}')

        # TITLE LABEL

        self.title_label = QLabel(self)
        self.title_label.setText("IMPINJ Reader Basic Interface")
        self.title_label.move(10, 10)
        self.title_label.resize(500, 25)
        self.title_label.setStyleSheet('QLabel {font:bold; font-size:24px}')

        # IP LABEL

        self.IP_label = QLabel(self)
        self.IP_label.setText("IP:")
        self.IP_label.move(10, 40)
        self.IP_label.resize(40, 40)
        self.IP_label.setStyleSheet('QLabel {font:bold; font-size:24px}')

        # PORT LABEL

        self.port_label = QLabel(self)
        self.port_label.setText("PORT:")
        self.port_label.move(270, 40)
        self.port_label.resize(80, 40)
        self.port_label.setStyleSheet('QLabel {font:bold; font-size:24px}')

        # CFG TITLE LABEL

        self.cfg_label = QLabel(self)
        self.cfg_label.setText("Configuration:")
        self.cfg_label.move(10, 170)
        self.cfg_label.resize(500, 40)
        self.cfg_label.setStyleSheet('QLabel {font:bold; font-size:24px}')

        # POWER LABEL

        self.cfg_label = QLabel(self)
        self.cfg_label.setText("POWER:")
        self.cfg_label.move(10, 465)
        self.cfg_label.resize(120, 40)
        self.cfg_label.setStyleSheet('QLabel {font-size:12px}')

        # ANTENNAS LABEL

        self.cfg_label = QLabel(self)
        self.cfg_label.setText("ANTENNA:")
        self.cfg_label.move(180, 465)
        self.cfg_label.resize(120, 40)
        self.cfg_label.setStyleSheet('QLabel {font-size:12px}')

        # MODE IDENTIFIER LABEL

        self.modeID_label = QLabel(self)
        self.modeID_label.setText("Mode Identifier:")
        self.modeID_label.move(10, 195)
        self.modeID_label.resize(120, 40)

        # SEARCH MODE LABEL

        self.searchMode_label = QLabel(self)
        self.searchMode_label.setText("Search Mode:")
        self.searchMode_label.move(180, 195)
        self.searchMode_label.resize(120, 40)

        # CHECKBOXES TAG CONTENT SELECTOR

        self.PeakRSSI = QCheckBox("Peak RSSI", self)
        self.PeakRSSI.stateChanged.connect(self.clickBox)
        self.PeakRSSI.move(10, 270)
        self.PeakRSSI.resize(320, 20)

        self.ROSpecID = QCheckBox("ROSpecID", self)
        self.ROSpecID.stateChanged.connect(self.clickBox)
        self.ROSpecID.move(10, 290)
        self.ROSpecID.resize(320, 20)

        self.SpecIndex = QCheckBox("SpecIndex", self)
        self.SpecIndex.stateChanged.connect(self.clickBox)
        self.SpecIndex.move(10, 310)
        self.SpecIndex.resize(320, 20)

        self.InventoryParameterSpecID = QCheckBox("InventoryParameterSpecID", self)
        self.InventoryParameterSpecID.stateChanged.connect(self.clickBox)
        self.InventoryParameterSpecID.move(10, 330)
        self.InventoryParameterSpecID.resize(320, 20)

        self.EnableAntennaID = QCheckBox("EnableAntennaID", self)
        self.EnableAntennaID.stateChanged.connect(self.clickBox)
        self.EnableAntennaID.move(10, 350)
        self.EnableAntennaID.resize(320, 20)

        self.ChannelIndex = QCheckBox("ChannelIndex", self)
        self.ChannelIndex.stateChanged.connect(self.clickBox)
        self.ChannelIndex.move(10, 370)
        self.ChannelIndex.resize(320, 20)

        self.FirstSeenTimestamp = QCheckBox("FirstSeenTimestamp", self)
        self.FirstSeenTimestamp.setChecked(True)
        self.FirstSeenTimestamp.stateChanged.connect(self.clickBox)
        self.FirstSeenTimestamp.move(10, 390)
        self.FirstSeenTimestamp.resize(320, 20)

        self.LastSeenTimestamp = QCheckBox("LastSeenTimestamp", self)
        self.LastSeenTimestamp.setChecked(True)
        self.LastSeenTimestamp.stateChanged.connect(self.clickBox)
        self.LastSeenTimestamp.move(10, 410)
        self.LastSeenTimestamp.resize(320, 20)

        self.TagSeenCount = QCheckBox("TagSeenCount", self)
        self.TagSeenCount.stateChanged.connect(self.clickBox)
        self.TagSeenCount.move(10, 430)
        self.TagSeenCount.resize(320, 20)

        self.EnableAccessSpecID = QCheckBox("EnableAccessSpecID", self)
        self.EnableAccessSpecID.stateChanged.connect(self.clickBox)
        self.EnableAccessSpecID.move(10, 450)
        self.EnableAccessSpecID.resize(320, 20)

        # MODE ID COMBO BOX

        self.mode_identifier = QComboBox(self)
        self.mode_identifier.addItem('Max Throughput')
        self.mode_identifier.addItem('Hybrid M=2')
        self.mode_identifier.addItem('Dense Reader M=4')
        self.mode_identifier.addItem('Dense Reader M=8')
        self.mode_identifier.addItem('Max Miller M=4')
        self.mode_identifier.addItem('Dense Reader 2 M=4')
        self.mode_identifier.resize(150, 20)

        self.mode_identifier.move(10, 225)

        self.mode_identifier.activated[str].connect(self.modeID_changed)

        # SEARCH MODE COMBO BOX

        self.search_mode = QComboBox(self)
        self.search_mode.addItem('Reader Selected (default)')
        self.search_mode.addItem('Single Target Inventory')
        self.search_mode.addItem('Dual Target Inventory')
        self.search_mode.addItem('Single Target Inventory with Suppression')
        self.search_mode.addItem('Single Target Reset Inventory')
        self.search_mode.addItem('Dual Target Inventory with Reset')
        self.search_mode.resize(200, 20)

        self.search_mode.move(180, 225)

        self.search_mode.activated[str].connect(self.searchMode_changed)

        # POWER SELECTOR

        self.search_mode = QComboBox(self)
        self.search_mode.addItem('MAXIMUM POWER')
        self.search_mode.addItem('90%')
        self.search_mode.addItem('85%')
        self.search_mode.addItem('80%')
        self.search_mode.addItem('70%')
        self.search_mode.addItem('60%')
        self.search_mode.addItem('50%')
        self.search_mode.addItem('40%')
        self.search_mode.addItem('30%')
        self.search_mode.addItem('20%')
        self.search_mode.addItem('10%')
        self.search_mode.resize(150, 20)

        self.search_mode.move(10, 495)

        self.search_mode.activated[str].connect(self.powerTX_changed)

        self.actual_power = 0

        # ANTENNA SELECTOR

        self.search_mode = QComboBox(self)
        self.search_mode.addItem('1')
        self.search_mode.addItem('2')
        self.search_mode.resize(150, 20)

        self.search_mode.move(180, 495)
        self.search_mode.activated[str].connect(self.antenna_changed)

        self.antenna_ID = DEFAULT_ANTENNA_LIST[0]

        # DATA TABLE

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setRowCount(16)
        self.table.setMinimumWidth(680)
        self.table.setMinimumHeight(512)
        self.table.move(500, 20)

        self.table.setHorizontalHeaderLabels(["PIG EPC", "ENTERED DRINK SPOT", "LEFT DRINK SPOT"])

        # TIMER TO ACTUALIZE TABLE

        self.timer = QTimer()
        self.timer.timeout.connect(self.actualize_table)
        self.timer.setInterval(500)
        self.timer.start()

        # TIMER TO ACTUALIZE LABELS

        self.label_refresh = QTimer()
        self.label_refresh.timeout.connect(self.actualize_labels)
        self.label_refresh.setInterval(4000)
        self.label_refresh.start()

        self.CarregaJanela()

    # METODO QUE ABRE UMA NOVA JANELA

    def CarregaJanela(self):
        self.setGeometry(self.esquerda, self.topo, self.largura, self.altura)
        self.setWindowTitle(self.titulo)
        self.show()

    # FUNCTIONS FOR CHECKBOXES
    def clickBox(self, state):
        if self.PeakRSSI.isChecked():
            factory_args['tag_content_selector']["EnablePeakRSSI"] = True
        else:
            factory_args['tag_content_selector']["EnablePeakRSSI"] = False

        if self.ROSpecID.isChecked():
            factory_args['tag_content_selector']["EnableROSpecID"] = True
        else:
            factory_args['tag_content_selector']["EnableROSpecID"] = False

        if self.SpecIndex.isChecked():
            factory_args['tag_content_selector']["EnableSpecIndex"] = True
        else:
            factory_args['tag_content_selector']["EnableSpecIndex"] = False

        if self.InventoryParameterSpecID.isChecked():
            factory_args['tag_content_selector']["EnableInventoryParameterSpecID"] = True
        else:
            factory_args['tag_content_selector']["EnableInventoryParameterSpecID"] = False

        if self.EnableAntennaID.isChecked():
            factory_args['tag_content_selector']["EnableAntennaID"] = True
        else:
            factory_args['tag_content_selector']["EnableAntennaID"] = False

        if self.ChannelIndex.isChecked():
            factory_args['tag_content_selector']["EnableChannelIndex"] = True
        else:
            factory_args['tag_content_selector']["EnableChannelIndex"] = False

        if self.FirstSeenTimestamp.isChecked():
            factory_args['tag_content_selector']["EnableFirstSeenTimestamp"] = True
        else:
            factory_args['tag_content_selector']["EnableFirstSeenTimestamp"] = False

        if self.LastSeenTimestamp.isChecked():
            factory_args['tag_content_selector']["EnableLastSeenTimestamp"] = True
        else:
            factory_args['tag_content_selector']["EnableLastSeenTimestamp"] = False

        if self.TagSeenCount.isChecked():
            factory_args['tag_content_selector']["EnableTagSeenCount"] = True
        else:
            factory_args['tag_content_selector']["EnableTagSeenCount"] = False

        if self.EnableAccessSpecID.isChecked():
            factory_args['tag_content_selector']["EnableAccessSpecID"] = True
        else:
            factory_args['tag_content_selector']["EnableAccessSpecID"] = False

    # FUNCTIONS FOR COMBOBOXES

    def modeID_changed(self, text):
        if text == 'Max Throughput':
            factory_args['mode_identifier'] = 0
        if text == 'Hybrid M=2':
            factory_args['mode_identifier'] = 1
        if text == 'Dense Reader M=4':
            factory_args['mode_identifier'] = 2
        if text == 'Dense Reader M=8':
            factory_args['mode_identifier'] = 3
        if text == 'Max Miller M=4':
            factory_args['mode_identifier'] = 4
        if text == 'Dense Reader 2 M=4':
            factory_args['mode_identifier'] = 5

    def searchMode_changed(self, text):
        if text == 'Reader Selected (default)':
            factory_args['search_mode'] = 0
        if text == 'Single Target Inventory':
            factory_args['search_mode'] = 1
        if text == 'Dual Target Inventory':
            factory_args['search_mode'] = 2
        if text == 'Single Target Inventory with Suppression':
            factory_args['search_mode'] = 3
        if text == 'Single Target Reset Inventory':
            factory_args['search_mode'] = 4
        if text == 'Dual Target Inventory with Reset':
            factory_args['search_mode'] = 5

    def antenna_changed(self, text):
        if text == '1':
            self.antenna_ID = 0

        if text == '2':
            self.antenna_ID = 1

        factory_args['antennas'] = (DEFAULT_ANTENNA_LIST[self.antenna_ID],)
        factory_args['tx_power'] = {DEFAULT_ANTENNA_LIST[self.antenna_ID]: self.actual_power}

    def powerTX_changed(self, text):
        if text == 'MAXIMUM POWER':
            self.actual_power = 0
        if text == '90%':
            self.actual_power = 90
        if text == '85%':
            self.actual_power = 85
        if text == '80%':
            self.actual_power = 80
        if text == '70%':
            self.actual_power = 70
        if text == '60%':
            self.actual_power = 60
        if text == '50%':
            self.actual_power = 50
        if text == '40%':
            self.actual_power = 40
        if text == '30%':
            self.actual_power = 30
        if text == '20%':
            self.actual_power = 20
        if text == '10%':
            self.actual_power = 10

        # factory_args['tx_power'] = self.actual_power
        factory_args['tx_power'] = {DEFAULT_ANTENNA_LIST[self.antenna_ID]: self.actual_power}

    # METODO PARA EXECUTAR AÇÃO QUANDO CLICA NO BOTAO

    def botao1_click(self):
        self.IMPINJ.LLRP_DEFAULT_HOST = self.host_box.text()
        self.IMPINJ.LLRP_DEFAULT_PORT = int(self.port_box.text())

        if self.reader_connected == True:
            self.IMPINJ.disconnect()
            self.label_1.setText('Disconnected')
            self.botao1.setText('Connect')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"red"}')
            self.reader_connected = False
        else:
            self.label_1.setText('Tentando Conexão')
            self.connection_state = self.IMPINJ.connect()
            if self.connection_state == 0:
                self.label_1.setText('Connected')
                self.botao1.setText('Disconnect')
                self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"green"}')
                self.reader_connected = True
            elif self.connection_state == 2:
                self.label_1.setText('Already Connected')
                self.botao1.setText('Disconnect')
                self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"green"}')
                self.reader_connected = True
            else:
                self.label_1.setText('Host Unreachable')
                self.botao1.setText('Connect')
                self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"red"}')

    def botao2_click(self):
        if self.reader_connected:
            self.IMPINJ.update_cfg()
            self.label_1.setText('Configuration updated')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"blue"}')
        else:
            self.label_1.setText('Reader is not connected')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"red"}')

    def actualize_table(self):
        rowPosition = self.table.rowCount()
        if self.internal_list_size != len(list_intern_table):
            self.table.setItem(self.internal_list_size, 0,
                               QTableWidgetItem(str(list_intern_table[self.internal_list_size]['EPC'])))
            self.table.setItem(self.internal_list_size, 1, QTableWidgetItem(
                str(list_intern_table[self.internal_list_size]['FirstSeenTimestampUTC'])))
            self.table.setItem(self.internal_list_size, 2, QTableWidgetItem(
                str(list_intern_table[self.internal_list_size]['LastSeenTimestampUTC'])))
            self.internal_list_size += 1
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()

    def actualize_labels(self):
        self.connection_state = self.IMPINJ.connection_status()
        if self.connection_state == 0:
            self.label_1.setText('Connected')
            self.botao1.setText('Disconnect')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"green"}')

        elif self.connection_state == 2:
            self.label_1.setText('Already Connected')
            self.botao1.setText('Disconnect')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"green"}')

        else:
            self.label_1.setText('Disconnected')
            self.botao1.setText('Connect')
            self.label_1.setStyleSheet('QLabel {font:bold; font-size:25px; color:"red"}')


a = Th(1)
a.start()


def main():
    app = QApplication(sys.argv)
    j = MainWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

