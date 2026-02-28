from models import DiaryEntryModel, PatientProfileModel, HealthAlertModel
import const
from psycopg2.pool import SimpleConnectionPool

def get_pool():
    return SimpleConnectionPool(
        minconn=const.DB_MIN_CONN,
        maxconn=const.DB_MAX_CONN,
        dbname=const.DB_NAME,
        user=const.DB_USER,
        password=const.DB_PASSWORD,
        host=const.DB_HOST,
        port=const.DB_PORT,
    )

def get_db_connection():
    return get_pool().getconn()


def create_tables():
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_CREATE_TABLES)


def create_indices():
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_CREATE_INDICES)


def init_db():
    create_tables()
    create_indices()


def insert_diary_entry(diary_entry: DiaryEntryModel) -> DiaryEntryModel:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_INSERT_DIARY_ENTRY_RETURNING_ID,
            (diary_entry.timestamp, diary_entry.patientProfileId, diary_entry.moodLevel, diary_entry.emotions, diary_entry.healthComplaints, diary_entry.foodIntake, diary_entry.notes, diary_entry.suggestion)
        )
        diary_entry_id = cursor.fetchone()[0]
        get_db_connection().commit()
        inserted = DiaryEntryModel(
            timestamp=diary_entry.timestamp,
            patientProfileId=diary_entry.patientProfileId,
            moodLevel=diary_entry.moodLevel,
            emotions=diary_entry.emotions,
            healthComplaints=diary_entry.healthComplaints,
            foodIntake=diary_entry.foodIntake,
            notes=diary_entry.notes,
            suggestion=diary_entry.suggestion
        )
        inserted.id = diary_entry_id
        return inserted


def insert_patient_profile(patient: PatientProfileModel) -> PatientProfileModel:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_INSERT_PATIENT_RETURNING_ID,
            (patient.name, patient.languageCode, patient.tajNumber, patient.chronicIllnesses, patient.allergies, patient.drugSensitivities, patient.dateOfBirth)
        )
        patient_profile_id = cursor.fetchone()[0]
        get_db_connection().commit()
        inserted = PatientProfileModel(
            name=patient.name,
            tajNumber=patient.tajNumber,
            languageCode=patient.languageCode,
            chronicIllnesses=patient.chronicIllnesses,
            allergies=patient.allergies,
            drugSensitivities=patient.drugSensitivities,
            dateOfBirth=patient.dateOfBirth,
        )
        inserted.id = patient_profile_id
        return inserted


def insert_health_alert(health_alert: HealthAlertModel) -> HealthAlertModel:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_INSERT_HEALTH_ALERT_RETURNING_ID,
            (health_alert.patientProfileId, health_alert.title, health_alert.message, health_alert.timestamp, health_alert.isRead, health_alert.severity)
        )
        health_alert_id = cursor.fetchone()[0]
        get_db_connection().commit()
        inserted = HealthAlertModel(
            patientProfileId=health_alert.patientProfileId,
            title=health_alert.title,
            message=health_alert.message,
            timestamp=health_alert.timestamp,
            isRead=health_alert.isRead,
            severity=health_alert.severity,
        )
        inserted.id = health_alert_id
        return inserted


def update_diary_entry(id: int, diary_entry: DiaryEntryModel) -> DiaryEntryModel | None:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_UPDATE_DIARY_ENTRY,
            (diary_entry.timestamp, diary_entry.patientProfileId, diary_entry.moodLevel,
             diary_entry.emotions, diary_entry.healthComplaints, diary_entry.foodIntake,
             diary_entry.notes, diary_entry.suggestion, id)
        )
        if cursor.rowcount == 0:
            return None
    return find_diary_entry_by_id(id)


def delete_diary_entry(id: int) -> bool:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_DELETE_DIARY_ENTRY, (id,))
        return cursor.rowcount > 0


def update_patient_profile(id: int, patient: PatientProfileModel) -> PatientProfileModel | None:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_UPDATE_PATIENT,
            (patient.name, patient.languageCode, patient.tajNumber,
             patient.chronicIllnesses, patient.allergies, patient.drugSensitivities,
             patient.dateOfBirth, id)
        )
        if cursor.rowcount == 0:
            return None
    return find_patient_profile_by_id(id)


def delete_patient_profile(id: int) -> bool:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_DELETE_PATIENT, (id,))
        return cursor.rowcount > 0


def update_health_alert(id: int, patient_profile_id: int, health_alert: HealthAlertModel) -> HealthAlertModel | None:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            const.SQL_UPDATE_HEALTH_ALERT,
            (health_alert.patientProfileId, health_alert.title, health_alert.message,
             health_alert.timestamp, health_alert.isRead, health_alert.severity, id, patient_profile_id)
        )
        if cursor.rowcount == 0:
            return None
    return find_health_alert_by_id_and_patient_id(id, patient_profile_id)


def delete_health_alert_by_id_and_patient_id(id: int, patient_profile_id: int) -> bool:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_DELETE_HEALTH_ALERT, (id, patient_profile_id))
        return cursor.rowcount > 0


def delete_health_alerts_by_patient_id(patient_id: int) -> int:
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(const.SQL_DELETE_HEALTH_ALERTS_BY_PATIENT_ID, (patient_id,))
        return cursor.rowcount


def find_diary_entries_by_patient_profile_id(patient_id: int) -> list[DiaryEntryModel]:
    query = f"SELECT * FROM {const.SQL_DIARY_ENTRIES_TABLE_NAME}" \
        + " WHERE patient_profile_id = %s;"

    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query, [patient_id])
        rows = cursor.fetchall()

    diary_entries = []
    for row in rows:
        diary_entry_id, patientProfileId, timestamp, moodLevel, emotions, healthComplaints, foodIntake, notes, suggestion = row
        diary_entry = DiaryEntryModel(
            patientProfileId=patientProfileId,
            timestamp=timestamp,
            moodLevel=moodLevel,
            emotions=emotions,
            healthComplaints=healthComplaints,
            foodIntake=foodIntake,
            notes=notes,
            suggestion=suggestion
        )
        diary_entry.id = diary_entry_id
        diary_entries.append(diary_entry)

    return diary_entries


def find_diary_entry_by_id(id: int) -> DiaryEntryModel:
    query = f"SELECT * FROM {const.SQL_DIARY_ENTRIES_TABLE_NAME}" \
    + " WHERE id = %s;"
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query, [id])
        row = cursor.fetchone()

        diary_entry_id, patientProfileId, timestamp, moodLevel, emotions, healthComplaints, foodIntake, notes, suggestion = row

    diary_entry = DiaryEntryModel(
        patientProfileId=patientProfileId,
        timestamp=timestamp,
        moodLevel=moodLevel,
        emotions=emotions,
        healthComplaints=healthComplaints,
        foodIntake=foodIntake,
        notes=notes,
        suggestion=suggestion
    )
    diary_entry.id = diary_entry_id

    return diary_entry


def find_patient_profile_by_id(id: int) -> PatientProfileModel:
    query = f"SELECT * FROM {const.SQL_PATIENTS_TABLE_NAME}" \
    + " WHERE id = %s;"
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query, [id])
        row = cursor.fetchone()

        patient_profile_id, name, languageCode, tajNumber, chronicIllnesses, allergies, drugSensitivities, dateOfBirth = row

    patient_profile = PatientProfileModel(
        name=name,
        tajNumber=tajNumber,
        languageCode=languageCode,
        chronicIllnesses=chronicIllnesses,
        allergies=allergies,
        drugSensitivities=drugSensitivities,
        dateOfBirth=dateOfBirth,
    )

    patient_profile.id = patient_profile_id

    return patient_profile


def find_all_patient_profiles() -> list[PatientProfileModel]:
    patient_profiles = []
    query = f"SELECT * FROM {const.SQL_PATIENTS_TABLE_NAME}"
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

    for row in rows:

        patient_profile_id, name, languageCode, tajNumber, chronicIllnesses, allergies, drugSensitivities, dateOfBirth = row

        patient_profile = PatientProfileModel(
            name=name,
            tajNumber=tajNumber,
            languageCode=languageCode,
            chronicIllnesses=chronicIllnesses,
            allergies=allergies,
            drugSensitivities=drugSensitivities,
            dateOfBirth=dateOfBirth,
        )
        patient_profile.id = patient_profile_id

        patient_profiles.append(patient_profile)

    return patient_profiles


def find_health_alert_by_id_and_patient_id(id: int, patient_profile_id: int) -> HealthAlertModel:
    query = f"SELECT * FROM {const.SQL_HEALTH_ALERTS_TABLE_NAME}" \
    + " WHERE id = %s AND patient_profile_id = %s;"
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query, [id, patient_profile_id])
        row = cursor.fetchone()

        health_alert_id, patient_profile_id, title, message, timestamp, isRead, severity = row

    health_alert = HealthAlertModel(
        patientProfileId=patient_profile_id,
        title=title,
        message=message,
        timestamp=timestamp,
        isRead=isRead,
        severity=severity,
    )

    health_alert.id = health_alert_id

    return health_alert


def find_all_health_alerts_by_patient_id(patient_profile_id: int) -> list[HealthAlertModel]:
    health_alerts = []
    query = f"SELECT * FROM {const.SQL_HEALTH_ALERTS_TABLE_NAME}" \
    + " WHERE patient_profile_id = %s;"
    with get_db_connection() as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(query, [patient_profile_id])
        rows = cursor.fetchall()

    for row in rows:
        health_alert_id, patient_profile_id, title, message, timestamp, isRead, severity = row

        health_alert = HealthAlertModel(
            patientProfileId=patient_profile_id,
            title=title,
            message=message,
            timestamp=timestamp,
            isRead=isRead,
            severity=severity,
        )
        health_alert.id = health_alert_id

        health_alerts.append(health_alert)

    return health_alerts
