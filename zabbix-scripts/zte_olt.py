#!/usr/bin/env python3



from scrapli import Scrapli
import json
import argparse
import pymysql

def jpp(o):
    print(json.dumps(o, indent=2))

def print_all(o):

    for A in dir(o):
        if not(A.startswith("__")):
            a = repr(getattr(o, A))
            print("{} : {}".format(A, a))



def parse_reply_power_attenuation_info(reply_from_olt):
# разобрать ответ на запрос show pon power attenuation gpon-onu_1/1/1:{}"
    CURRENT_ONU = {}
    lines = reply_from_olt.result.split("\n")
    up_split = lines[2].split()
    down_split = lines[4].split()
    CURRENT_ONU["SIGNAL_LEVEL_UP_RX"] = up_split[2].replace("(dbm)", "").replace("Rx:","").replace(":", "")
    CURRENT_ONU["SIGNAL_LEVEL_UP_TX"] = up_split[3].replace("(dbm)", "").replace("Tx:","").replace(":", "")
    CURRENT_ONU["SIGNAL_LEVEL_UP_ATTENUATION"] = up_split[4].replace("(dB)", "")
    CURRENT_ONU["SIGNAL_LEVEL_DOWN_RX"] = down_split[3].replace("(dbm)", "").replace("Rx:","").replace(":", "")
    CURRENT_ONU["SIGNAL_LEVEL_DOWN_TX"] = down_split[2].replace("(dbm)", "").replace("Tx:","").replace(":", "")
    CURRENT_ONU["SIGNAL_LEVEL_DOWN_ATTENUATION"] = down_split[4].replace("(dB)", "")

    return CURRENT_ONU


def parse_reply_detail_info(reply_from_olt):
# Разобрать ответ от запроса show gpon onu detail-info gpon-onu_1/1/1:{}"
    CURRENT_ONU = {}
    lines = reply_from_olt.result.split("\n")
    i = 0
    for line in lines[0:27]:
        i = i + 1
        line_split = line.split(":", 1)
        object_name = "{}".format(line_split[0].strip().replace(":", "").replace(" ", "_").replace("+", "__").upper())
        object_value = line_split[1].strip()
        if object_name == "ONU_DISTANCE":
            # Удалить размерность (иначе заббикс не поймет что это цифра а не строка)
            object_value = object_value.replace("m", "")

        if object_name == "DESCRIPTION":
            object_value = object_value.replace('"', "").replace("'", "")

        CURRENT_ONU[object_name] = object_value


    CURRENT_ONU["ACTIVE_SESSION_START_DATE"] = "0000-00-00"
    CURRENT_ONU["ACTIVE_SESSION_START_TIME"] = "00:00:00"

    CURRENT_ONU["PREV_SESSION_REASON"] = "undef"
    CURRENT_ONU["PREV_SESSION_START_DATE"] = "0000-00-00"
    CURRENT_ONU["PREV_SESSION_START_TIME"] = "00:00:00"
    CURRENT_ONU["PREV_SESSION_END_DATE"] = "0000-00-00"
    CURRENT_ONU["PREV_SESSION_END_TIME"] = "00:00:00"

    for line in lines[30:]:
        l = line.split()[1:]
        # Все запими где время старта сессии не опрелено - пропускать
        if l[0] == "0000-00-00":
            continue
        #print(l)
        if l[2] ==  "0000-00-00":
            # Если время окончания сессии не выставлено - значит сессия активна
            CURRENT_ONU["ACTIVE_SESSION_START_DATE"] = l[0]
            CURRENT_ONU["ACTIVE_SESSION_START_TIME"] = l[1]
        else:
            CURRENT_ONU["PREV_SESSION_START_DATE"] = l[0]
            CURRENT_ONU["PREV_SESSION_START_TIME"] = l[1]
            CURRENT_ONU["PREV_SESSION_END_DATE"] = l[2]
            CURRENT_ONU["PREV_SESSION_END_TIME"] = l[3]
            CURRENT_ONU["PREV_SESSION_REASON"] = l[4]

    return CURRENT_ONU


def get_onu_data_from_olt(device):

    SHOW_GPON_ONU_STATE="show gpon onu state"
    ALL_ONU=[]
    device_config = device["config"]
    conn = Scrapli(**device_config)
    conn.open()
    reply_from_olt = conn.send_command(SHOW_GPON_ONU_STATE, failed_when_contains=["%Error "])
    gpon_onu_state = reply_from_olt.result.split("\n")

    for line in gpon_onu_state[2:-1]:
        L=line.split()
        ONU_NUMBER=L[0].split(":")[1]
        CURRENT_ONU = {}
        CURRENT_ONU["OLT_IP"] = device_config["host"]
        CURRENT_ONU["OLT_NAME"] = device["name"]
        CURRENT_ONU["ONU"] = L[0]
        CURRENT_ONU["{#ONU_FULL_ID}"] = "{}-{}".format(device_config["host"], L[0])
        CURRENT_ONU["ONU_NUMBER"] = ONU_NUMBER
        CURRENT_ONU["ONU_ADMIN_STATE"]=L[1]
        CURRENT_ONU["ONU_OMCC_STATE"]=L[2]
        CURRENT_ONU["ONU_PHASE_STATE"]=L[3]
        CURRENT_ONU["ONU_CHANNEL"]=L[4]

        # Получить подробную информацию
        cmd = "show gpon onu detail-info gpon-onu_1/1/1:{}".format(CURRENT_ONU["ONU_NUMBER"])
        reply_from_olt = conn.send_command(cmd, failed_when_contains=["%Error "])

        a = parse_reply_detail_info(reply_from_olt)
        # это способ соединить 2 дикта
        CURRENT_ONU = {**CURRENT_ONU, **a}

        # Получить число МАК-адресов
        cmd = "show mac gpon onu gpon-onu_1/1/1:{}".format(CURRENT_ONU["ONU_NUMBER"])
        reply_from_olt = conn.send_command(cmd, failed_when_contains=["%Error "])
        lines = reply_from_olt.result.split("\n")
        CURRENT_ONU["TOTAL_MAC_ADDRESSES"] = lines[0].split(":")[1].strip()

        #ONU уровни сигнала (оптического)
        cmd = "show pon power attenuation gpon-onu_1/1/1:{}".format(CURRENT_ONU["ONU_NUMBER"])
        reply_from_olt = conn.send_command(cmd, failed_when_contains=["%Error "])
        a = parse_reply_power_attenuation_info(reply_from_olt)

        # это способ соединить 2 дикта
        CURRENT_ONU = {**CURRENT_ONU, **a}
        ALL_ONU.append(CURRENT_ONU)


    return(ALL_ONU)




if __name__ == "__main__":
    ALL_ONU_ON_ALL_OLT = []
    parser = argparse.ArgumentParser(description="",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--config", help="Path to the configuration file", default="config.json")
    parser.add_argument("-m", "--mysql-config", help="Path to the database credentials configuration file", default="mysql.json")
    parser.add_argument("-o", "--output", help="Path where save outputs", default=".")

    args = parser.parse_args()
    config = vars(args)

    with open(config["config"], 'r') as file:
        configuration = json.load(file)


    for OLT in configuration['devices']:
        ALL_ONU_ON_ALL_OLT = ALL_ONU_ON_ALL_OLT + get_onu_data_from_olt(OLT)

    result_file =  "{}/{}".format(config["output"], "zte.json")
    with open(result_file, 'w') as file:
        file.write(json.dumps(ALL_ONU_ON_ALL_OLT, indent=2))


    with open(config["mysql_config"], 'r') as file:
        mysql_configuration = json.load(file)

    connection = pymysql.connect(host=mysql_configuration['host'],
                                 user=mysql_configuration['user'],
                                 password=mysql_configuration['password'],
                                 database=mysql_configuration['database'],
                                 cursorclass=pymysql.cursors.DictCursor)
    with connection:
        with connection.cursor() as cursor:
            # Create a new record
            sql = """REPLACE INTO `{}`
                    (
                    `OLT_IP`,                   `OLT_NAME`,                     `ONU`,
                    `ONU_FULL_ID`,              `ONU_NUMBER`,                   `ONU_ADMIN_STATE`,
                    `ONU_OMCC_STATE`,           `ONU_PHASE_STATE`,              `ONU_CHANNEL`,
                    `ONU_INTERFACE`,            `NAME`,                         `TYPE`,
                    `STATE`,                    `CONFIGURED_CHANNEL`,           `CURRENT_CHANNEL`,
                    `ADMIN_STATE`,              `PHASE_STATE`,                  `CONFIG_STATE`,
                    `AUTHENTICATION_MODE`,      `SN_BIND`,                      `SERIAL_NUMBER`,
                    `PASSWORD`,                 `DESCRIPTION`,                  `VPORT_MODE`,
                    `DBA_MODE`,                 `ONU_STATUS`,                   `OMCI_BW_PROFILE`,
                    `LINE_PROFILE`,             `SERVICE_PROFILE`,              `ONU_DISTANCE`,
                    `ONLINE_DURATION`,          `FEC`,                          `FEC_ACTUAL_MODE`,
                    `PPS__TOD`,                 `AUTO_REPLACE`,                 `MULTICAST_ENCRYPTION`,
                    `ACTIVE_SESSION_START_DATE`,`ACTIVE_SESSION_START_TIME`,    `PREV_SESSION_REASON`,
                    `PREV_SESSION_START_DATE`,  `PREV_SESSION_START_TIME`,      `PREV_SESSION_END_DATE`,
                    `PREV_SESSION_END_TIME`,    `TOTAL_MAC_ADDRESSES`,          `SIGNAL_LEVEL_UP_RX`,
                    `SIGNAL_LEVEL_UP_TX`,       `SIGNAL_LEVEL_UP_ATTENUATION`,  `SIGNAL_LEVEL_DOWN_RX`,
                    `SIGNAL_LEVEL_DOWN_TX`,     `SIGNAL_LEVEL_DOWN_ATTENUATION`
                    )
                        VALUES (
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s
                        )
                """
            sql = sql.format(mysql_configuration['pon_table'])
            for ONU in ALL_ONU_ON_ALL_OLT:
                values = (
                    ONU["OLT_IP"],                      ONU["OLT_NAME"],                        ONU["ONU"],
                    ONU["{#ONU_FULL_ID}"],              int(ONU["ONU_NUMBER"]),                 ONU["ONU_ADMIN_STATE"],
                    ONU["ONU_OMCC_STATE"],              ONU["ONU_PHASE_STATE"],                 ONU["ONU_CHANNEL"],
                    ONU["ONU_INTERFACE"],               ONU["NAME"],                            ONU["TYPE"],
                    ONU["STATE"],                       ONU["CONFIGURED_CHANNEL"],              ONU["CURRENT_CHANNEL"],
                    ONU["ADMIN_STATE"],                 ONU["PHASE_STATE"],                     ONU["CONFIG_STATE"],
                    ONU["AUTHENTICATION_MODE"],         ONU["SN_BIND"],                         ONU["SERIAL_NUMBER"],
                    ONU["PASSWORD"],                    ONU["DESCRIPTION"],                     ONU["VPORT_MODE"],
                    ONU["DBA_MODE"],                    ONU["ONU_STATUS"],                      ONU["OMCI_BW_PROFILE"],
                    ONU["LINE_PROFILE"],                ONU["SERVICE_PROFILE"],                 ONU["ONU_DISTANCE"],
                    ONU["ONLINE_DURATION"],             ONU["FEC"],                             ONU["FEC_ACTUAL_MODE"],
                    ONU["1PPS__TOD"],                   ONU["AUTO_REPLACE"],                    ONU["MULTICAST_ENCRYPTION"],
                    ONU["ACTIVE_SESSION_START_DATE"],   ONU["ACTIVE_SESSION_START_TIME"],       ONU["PREV_SESSION_REASON"],
                    ONU["PREV_SESSION_START_DATE"],     ONU["PREV_SESSION_START_TIME"],         ONU["PREV_SESSION_END_DATE"],
                    ONU["PREV_SESSION_END_TIME"],       ONU["TOTAL_MAC_ADDRESSES"],             ONU["SIGNAL_LEVEL_UP_RX"],
                    ONU["SIGNAL_LEVEL_UP_TX"],          ONU["SIGNAL_LEVEL_UP_ATTENUATION"],     ONU["SIGNAL_LEVEL_DOWN_RX"],
                    ONU["SIGNAL_LEVEL_DOWN_TX"],        ONU["SIGNAL_LEVEL_DOWN_ATTENUATION"]
                )

                #print(sql % values)

                cursor.execute(sql, values)
                connection.commit()
