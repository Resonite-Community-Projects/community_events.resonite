from enum import Enum

class CEEnum(str, Enum):

    @classmethod
    def valid_values(cls):
        return '\n- '.join([''] + [f"{cls.__name__}.{member.name}: '{cls.__name__}.{member.value}'" for member in cls])

class SignalSchedulerType(CEEnum):
    """
    Enum representing the different scheduling types for signal collectors and transmitters.

    The scheduling type determines which Python module will handle the signals schedule:

    - APSCHEDULER: Uses the APScheduler module for scheduling signals in a more common way.
    - DISCORD: Uses the Disnake module for managing signals related to Discord.
    """

    APSCHEDULER = 'apscheduler'
    """
    Signal uses the APScheduler module to schedule tasks.
    
    Signals with this type will be scheduled via the AsyncIOScheduler.
    """

    DISCORD = 'discord'
    """
    Signal uses the Disnake module ot handle discord related tasks.

    Signals with this type will be integrated into Disnake bot as cogs.
    """