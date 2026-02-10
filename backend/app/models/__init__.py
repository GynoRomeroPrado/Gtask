# Modelos SQLAlchemy — Cerebro Operativo
# Importar todos los modelos para que Base.metadata los conozca
from app.models.task import Task, TaskDependency  # noqa
from app.models.task_list import TaskList  # noqa
from app.models.tag import Tag  # noqa
from app.models.event import Event, FinancialAlert  # noqa
from app.models.conversation import Conversation  # noqa
from app.models.health_goal import HealthGoal  # noqa
