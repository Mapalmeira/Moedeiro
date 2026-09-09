from pydantic import BaseModel, Field

from app.infrastructure.persistence.sqlite.ledger.default_labels import CATEGORY_LABELS, CURRENCY_LABELS
from app.domain.appearance import Icon, RgbColorCode
from app.domain.registry.model.user_preferences import Language


class CurrencyDefault(BaseModel):
    key: str
    prefix: str | None
    suffix: str | None
    decimal_places: int = Field(ge=0, le=20)
    icon: Icon
    color_code: RgbColorCode


class CategoryDefault(BaseModel):
    key: str
    icon: Icon
    color_code: RgbColorCode
    children: tuple["CategoryDefault", ...] = ()


AMBER = bytes.fromhex("D97706")
BLUE = bytes.fromhex("2563EB")
BLUE_EURO = bytes.fromhex("003399")
BROWN = bytes.fromhex("AE5400")
CYAN = bytes.fromhex("0891B2")
GOLD = bytes.fromhex("CA8A04")
GREEN = bytes.fromhex("16A34A")
INDIGO = bytes.fromhex("4F46E5")
ORANGE = bytes.fromhex("EA580C")
PINK = bytes.fromhex("DB2777")
PURPLE = bytes.fromhex("7C3AED")
PURPLE_POUND = bytes.fromhex("5B2C6F")
RED = bytes.fromhex("DC2626")
RED_JAPAN = bytes.fromhex("BC002D")
ROSE = bytes.fromhex("E11D48")
SLATE = bytes.fromhex("64748B")
TEAL = bytes.fromhex("0F766E")
YELLOW = bytes.fromhex("F59E0B")


CATEGORY_TREE: tuple[CategoryDefault, ...] = (
    CategoryDefault(
        key="food",
        icon="lucide:Utensils",
        color_code=ORANGE,
        children=(
            CategoryDefault(key="groceries", icon="lucide:ShoppingBasket", color_code=ORANGE),
            CategoryDefault(key="restaurants", icon="lucide:CookingPot", color_code=ORANGE),
            CategoryDefault(key="snacks", icon="lucide:Coffee", color_code=GOLD),
        ),
    ),
    CategoryDefault(
        key="housing",
        icon="lucide:House",
        color_code=RED,
        children=(
            CategoryDefault(key="rent", icon="lucide:Building2", color_code=RED),
            CategoryDefault(key="condominium", icon="lucide:Building", color_code=RED),
            CategoryDefault(
                key="household_bills",
                icon="lucide:Lightbulb",
                color_code=YELLOW,
                children=(
                    CategoryDefault(key="electricity", icon="lucide:Zap", color_code=YELLOW),
                    CategoryDefault(key="water", icon="lucide:Waves", color_code=CYAN),
                    CategoryDefault(key="gas", icon="lucide:Flame", color_code=YELLOW),
                    CategoryDefault(key="internet", icon="lucide:Wifi", color_code=BLUE),
                    CategoryDefault(key="cellphone", icon="lucide:Smartphone", color_code=BLUE),
                ),
            ),
            CategoryDefault(
                key="decoration",
                icon="lucide:Lamp",
                color_code=AMBER,
            ),
        ),
    ),
    CategoryDefault(
        key="transport",
        icon="lucide:Car",
        color_code=BLUE,
        children=(
            CategoryDefault(key="rides", icon="lucide:MapPin", color_code=BLUE),
            CategoryDefault(key="fuel", icon="lucide:Fuel", color_code=BLUE),
            CategoryDefault(key="public_transport", icon="lucide:TrainFront", color_code=BLUE),
        ),
    ),
    CategoryDefault(
        key="health",
        icon="lucide:HeartPulse",
        color_code=RED,
        children=(
            CategoryDefault(key="pharmacy", icon="lucide:Pill", color_code=RED),
            CategoryDefault(key="therapy", icon="lucide:Brain", color_code=RED),
            CategoryDefault(key="appointments", icon="lucide:Stethoscope", color_code=RED),
        ),
    ),
    CategoryDefault(
        key="education",
        icon="lucide:GraduationCap",
        color_code=PURPLE,
        children=(
            CategoryDefault(key="books", icon="lucide:BookOpen", color_code=PURPLE),
            CategoryDefault(key="courses", icon="lucide:NotebookPen", color_code=PURPLE),
        ),
    ),
    CategoryDefault(
        key="leisure",
        icon="lucide:PartyPopper",
        color_code=PINK,
        children=(
            CategoryDefault(key="games", icon="lucide:Gamepad2", color_code=PINK),
            CategoryDefault(key="events", icon="lucide:Ticket", color_code=PINK),
            CategoryDefault(key="cinema", icon="lucide:Clapperboard", color_code=PINK),
            CategoryDefault(key="travel", icon="lucide:Luggage", color_code=PINK),
        ),
    ),
    CategoryDefault(
        key="subscriptions",
        icon="lucide:Repeat2",
        color_code=INDIGO,
        children=(
            CategoryDefault(key="streaming", icon="lucide:Play", color_code=INDIGO),
            CategoryDefault(key="digital_services", icon="lucide:MonitorSmartphone", color_code=INDIGO),
        ),
    ),
    CategoryDefault(
        key="electronics",
        icon="lucide:Laptop",
        color_code=TEAL,
        children=(
            CategoryDefault(key="peripherals", icon="lucide:Keyboard", color_code=TEAL),
            CategoryDefault(key="hardware", icon="lucide:Cpu", color_code=TEAL),
        ),
    ),
    CategoryDefault(
        key="tools",
        icon="lucide:Hammer",
        color_code=SLATE,
    ),
    CategoryDefault(
        key="gifts",
        icon="lucide:Gift",
        color_code=ROSE,
        children=(
            CategoryDefault(key="special_dates", icon="lucide:Cake", color_code=ROSE),
            CategoryDefault(key="casual_gift", icon="lucide:Gift", color_code=ROSE),
        ),
    ),
    CategoryDefault(
        key="services",
        icon="lucide:ConciergeBell",
        color_code=CYAN,
        children=(
            CategoryDefault(key="maintenance", icon="lucide:Wrench", color_code=CYAN),
            CategoryDefault(key="personal_care", icon="lucide:Scissors", color_code=CYAN),
        ),
    ),
    CategoryDefault(
        key="loans",
        icon="lucide:HandCoins",
        color_code=SLATE,
    ),
    CategoryDefault(
        key="clothing",
        icon="lucide:Shirt",
        color_code=PINK,
    ),
    CategoryDefault(
        key="taxes",
        icon="lucide:Landmark",
        color_code=SLATE,
        children=(
            CategoryDefault(key="income_tax", icon="lucide:FileText", color_code=SLATE),
        ),
    ),
    CategoryDefault(
        key="income",
        icon="lucide:TrendingUp",
        color_code=GREEN,
        children=(
            CategoryDefault(key="salary", icon="lucide:BanknoteArrowUp", color_code=GREEN),
            CategoryDefault(key="allowance", icon="lucide:WalletCards", color_code=GREEN),
            CategoryDefault(key="scholarship", icon="lucide:GraduationCap", color_code=GREEN),
        ),
    ),
    CategoryDefault(
        key="transfers",
        icon="lucide:ArrowLeftRight",
        color_code=SLATE,
        children=(
            CategoryDefault(key="investments", icon="lucide:ChartNoAxesCombined", color_code=SLATE),
        ),
    ),
    CategoryDefault(
        key="donation",
        icon="lucide:HandHeart",
        color_code=ROSE,
        children=(
            CategoryDefault(key="one_off_donation", icon="lucide:HandHeart", color_code=ROSE),
            CategoryDefault(key="recurring_donation", icon="lucide:HeartHandshake", color_code=ROSE),
        ),
    ),
)


DEFAULT_CURRENCIES: tuple[CurrencyDefault, ...] = (
    CurrencyDefault(key="brl", prefix="R$ ", suffix=None, decimal_places=2, icon="unicode:R$", color_code=GREEN),
    CurrencyDefault(key="usd", prefix="US$ ", suffix=None, decimal_places=2, icon="lucide:DollarSign", color_code=BLUE),
    CurrencyDefault(key="eur", prefix="€ ", suffix=None, decimal_places=2, icon="lucide:Euro", color_code=BLUE_EURO),
    CurrencyDefault(key="btc", prefix=None, suffix=" BTC", decimal_places=8, icon="lucide:Bitcoin", color_code=BROWN),
    CurrencyDefault(key="jpy", prefix="¥ ", suffix=None, decimal_places=0, icon="lucide:JapaneseYen", color_code=RED_JAPAN),
    CurrencyDefault(key="gbp", prefix="£ ", suffix=None, decimal_places=2, icon="lucide:PoundSterling", color_code=PURPLE_POUND),
)


def category_name(key: str, language: Language) -> str:
    return CATEGORY_LABELS[language][key]


def currency_name(key: str, language: Language) -> str:
    return CURRENCY_LABELS[language][key]


def default_currencies(language: Language) -> tuple[tuple[str, str | None, str | None, int, Icon, RgbColorCode], ...]:
    return tuple(
        (
            currency_name(currency.key, language),
            currency.prefix,
            currency.suffix,
            currency.decimal_places,
            currency.icon,
            currency.color_code,
        )
        for currency in DEFAULT_CURRENCIES
    )
