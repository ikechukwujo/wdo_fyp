from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

DATABASE_URL = "postgresql://postgres:ikpostgres*@localhost:5432/water_optimizer"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    id = Column(String, primary_key=True)
    status = Column(String)
    network_file = Column(String)
    population_size = Column(Integer)
    num_generations = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class OptimizationResult(Base):
    __tablename__ = "optimization_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String)
    pareto_front = Column(JSON)
    knee_solution = Column(JSON)
    hypervolume = Column(Float)
    pareto_front_size = Column(Integer)
    baseline = Column(JSON)
    summary_table = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def save_run(job_id: str, result: dict, baseline: dict, summary: dict):
    session = SessionLocal()
    try:
        db_result = OptimizationResult(
            run_id=job_id,
            pareto_front=result['pareto_front'],
            knee_solution=result['knee_solution'],
            hypervolume=result.get('hypervolume', 0),
            pareto_front_size=result.get('pareto_front_size', 0),
            baseline=baseline,
            summary_table=summary
        )
        session.add(db_result)
        session.commit()
        print(f"Results saved for job {job_id}")
    except Exception as e:
        print(f"Database save error: {e}")
        session.rollback()
    finally:
        session.close()


def get_all_runs():
    session = SessionLocal()
    try:
        results = session.query(OptimizationResult).all()
        return [
            {
                'run_id': r.run_id,
                'pareto_front_size': r.pareto_front_size,
                'hypervolume': r.hypervolume,
                'created_at': str(r.created_at)
            }
            for r in results
        ]
    finally:
        session.close()


if __name__ == "__main__":
    init_db()