from sqlalchemy.orm import Session

from database.models import IngestionStat, PredictionLog


def create_prediction(
    db: Session,
    prediction: PredictionLog,
):

    db.add(prediction)

    db.commit()

    db.refresh(prediction)

    return prediction


def create_ingestion_stat(db: Session, stat: IngestionStat):

    db.add(stat)

    db.commit()

    db.refresh(stat)

    return stat
