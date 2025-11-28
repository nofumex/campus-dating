"""FSM состояния для бота."""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации."""
    waiting_for_university = State()
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_looking_for = State()
    waiting_for_photo = State()
    waiting_for_bio = State()
    confirm_profile = State()


class EditProfileStates(StatesGroup):
    """Состояния редактирования профиля."""
    choosing_what_to_edit = State()
    editing_name = State()
    editing_age = State()
    editing_gender = State()
    editing_looking_for = State()
    editing_photo = State()
    editing_bio = State()
    editing_university = State()


class ProfileMenuStates(StatesGroup):
    """Состояние меню профиля."""
    in_profile_menu = State()


class ViewingStates(StatesGroup):
    """Состояния просмотра анкет."""
    viewing_profiles = State()
    writing_message = State()


class LikesStates(StatesGroup):
    """Состояния просмотра лайков."""
    confirming_view = State()
    viewing_likes = State()


class MatchesStates(StatesGroup):
    """Состояния просмотра мэтчей."""
    viewing_matches = State()


class ReportStates(StatesGroup):
    """Состояния жалобы."""
    choosing_reason = State()
    writing_comment = State()


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    main_menu = State()
    adding_university = State()
    editing_university = State()
    viewing_reports = State()
    banning_user = State()
    broadcast_message = State()

