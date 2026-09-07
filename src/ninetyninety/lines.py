"""The IRS Form 990-EZ Part I line taxonomy.

Single source of truth for the parser, the validation harness, the agents and
the PDF filler. Every `xml_element` was read from live IRS e-file XML on
2026-09-06 -- guessing two of these names cost 12.5% reconstruction accuracy.

`guidance` is what the Preparer and Reviewer agents see. Keep it short and
plainly derived from the Form 990-EZ instructions (i990ez.pdf).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    number: str
    label: str
    xml_element: str
    kind: str  # "revenue" or "expense"
    guidance: str


REVENUE_LINES: list[Line] = [
    Line("1", "Contributions, gifts, grants, and similar amounts received",
         "ContributionsGiftsGrantsEtcAmt", "revenue",
         "Voluntary transfers where the donor receives nothing of comparable "
         "value in return: donations, grants from foundations or government, "
         "bequests, and the contribution portion of a fundraising ticket."),
    Line("2", "Program service revenue including government fees and contracts",
         "ProgramServiceRevenueAmt", "revenue",
         "Income earned by carrying out the organisation's exempt purpose: "
         "tuition, admissions, class fees, service fees paid by clients or by "
         "a government agency buying the service."),
    Line("3", "Membership dues and assessments",
         "MembershipDuesAmt", "revenue",
         "Dues paid to belong to the organisation. If members receive benefits "
         "of comparable value the payment belongs on line 3; if it is really a "
         "donation with no benefit it belongs on line 1."),
    Line("4", "Investment income",
         "InvestmentIncomeAmt", "revenue",
         "Interest, dividends, and rent from investment property. Bank account "
         "interest belongs here."),
    Line("5c", "Gain or (loss) from sale of assets other than inventory",
         "GainOrLossFromSaleOfAssetsAmt", "revenue",
         "Net gain or loss from selling equipment, vehicles or securities. This "
         "is a NET figure -- proceeds minus basis -- and may be negative."),
    Line("6d", "Net income or (loss) from gaming and fundraising events",
         "SpecialEventsNetIncomeLossAmt", "revenue",
         "Gross receipts from events such as galas, raffles and bingo, minus the "
         "direct expenses of those events. NET, and may be negative."),
    Line("7c", "Gross profit or (loss) from sales of inventory",
         "GrossProfitLossSlsOfInvntryAmt", "revenue",
         "Sales of goods (merchandise, cookbooks, thrift goods) minus cost of "
         "goods sold. NET, and may be negative."),
    Line("8", "Other revenue",
         "OtherRevenueTotalAmt", "revenue",
         "Revenue that fits none of lines 1 through 7c. Use sparingly; prefer a "
         "specific line whenever one applies."),
]

EXPENSE_LINES: list[Line] = [
    Line("10", "Grants and similar amounts paid",
         "GrantsAndSimilarAmountsPaidAmt", "expense",
         "Grants, scholarships and assistance the organisation pays out to "
         "others, including direct aid to the people it serves."),
    Line("11", "Benefits paid to or for members",
         "BenefitsPaidToOrForMembersAmt", "expense",
         "Payments made to members as members, such as insurance or death "
         "benefits from a fraternal or mutual organisation."),
    Line("12", "Salaries, other compensation, and employee benefits",
         "SalariesOtherCompEmplBnftAmt", "expense",
         "Wages, payroll taxes, pension and health benefits for EMPLOYEES. "
         "Payments to non-employees belong on line 13."),
    Line("13", "Professional fees and other payments to independent contractors",
         "FeesAndOtherPymtToIndCntrctAmt", "expense",
         "Payments to people and firms who are not employees: accountants, "
         "lawyers, consultants, contract cleaners, freelance instructors."),
    Line("14", "Occupancy, rent, utilities, and maintenance",
         "OccupancyRentUtltsAndMaintAmt", "expense",
         "Rent or mortgage interest on premises, electricity, gas, water, "
         "internet at the premises, cleaning and repairs to the premises."),
    Line("15", "Printing, publications, postage, and shipping",
         "PrintingPublicationsPostageAmt", "expense",
         "Printing, newsletters, stationery, stamps, courier and shipping."),
    Line("16", "Other expenses",
         "OtherExpensesTotalAmt", "expense",
         "Expenses fitting none of lines 10 through 15: insurance, software "
         "subscriptions, bank fees, supplies, travel, training."),
]

ALL_LINE_NUMBERS: set[str] = {
    line.number for line in REVENUE_LINES + EXPENSE_LINES
}

_BY_NUMBER = {line.number: line for line in REVENUE_LINES + EXPENSE_LINES}

# Part I order as printed on the form; "5c" sorts before "10" here, unlike str.
LINE_ORDER: list[str] = [line.number for line in REVENUE_LINES + EXPENSE_LINES]


def form_order(number: str) -> int:
    """Sort key placing line numbers in Form 990-EZ Part I order."""
    return LINE_ORDER.index(number)


def line_by_number(number: str) -> Line:
    return _BY_NUMBER[number]
