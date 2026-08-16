from collections import UserDict
from datetime import datetime, timedelta
from functools import wraps


# region --- Classes ---


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Birthday(Field):
    def __init__(self, value: str):
        try:
            birthday = datetime.strptime(value, "%d.%m.%Y").date()

            # Ensures strict DD.MM.YYYY format
            if birthday.strftime("%d.%m.%Y") != value:
                raise ValueError

        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

        super().__init__(birthday)


class Name(Field):
    """Necessary field for the contact's name."""

    pass


class Phone(Field):
    """Field for the contact's phone number with 10characters validation."""

    def __init__(self, value):
        if not self._is_valid_phone(value):
            raise ValueError("Phone number must contain exactly 10 digits.")

        super().__init__(value)

    @staticmethod
    def _is_valid_phone(phone_number: str) -> bool:
        return (
            isinstance(phone_number, str)
            and len(phone_number) == 10
            and phone_number.isdigit()
        )


class Record:
    """Class for storing contact information (name and list of phone numbers)"""

    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_birthday(self, birthday: str) -> None:
        self.birthday = Birthday(birthday)

    def add_phone(self, phone_number: str) -> None:
        """Adds a phone number to the list"""

        self.phones.append(Phone(phone_number))

    def remove_phone(self, phone_number: str) -> None:
        """Removes phone number from the list"""

        phone_object = self.find_phone(phone_number)

        if phone_object:
            self.phones.remove(phone_object)
        else:
            raise ValueError(f"Phone {phone_number} not found.")

    def edit_phone(self, old_phone_number: str, new_phone_number: str) -> None:
        """Edits existing phone number in the list"""

        phone = self.find_phone(old_phone_number)

        if phone is None:
            raise ValueError(f"Phone {old_phone_number} not found.")

        index = self.phones.index(phone)
        self.phones[index] = Phone(new_phone_number)

    def find_phone(self, phone_number: str) -> Phone | None:
        """Finds a phone number in the list and returns the PHone object"""

        for phone in self.phones:
            if phone.value == phone_number:
                return phone

        return None

    def __str__(self) -> str:
        return (
            f"Contact name: {self.name.value}, "
            f"phones: {'; '.join(p.value for p in self.phones)}"
        )


class AddressBook(UserDict[str, Record]):
    """Class for managing a collection of contact records."""

    def add_record(self, record: Record) -> None:
        """Adds a new record to the address book"""

        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        """Finds a record by name and returns the Record object"""

        return self.data.get(name)

    def delete(self, name: str) -> None:
        """Deletes a record by name"""

        if name in self.data:
            del self.data[name]
        else:
            raise ValueError(f"Record with name {name} not found.")

    def get_upcoming_birthdays(self, days: int = 7) -> list[dict[str, str]]:
        """Returns contacts whose birthdays occur within the next week."""

        upcoming_birthdays = []
        today = datetime.today().date()

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday = record.birthday.value

            # Birthday in the current year
            try:
                birthday_this_year = birthday.replace(year=today.year)
            except ValueError:
                # Handles February 29 in a non-leap year
                birthday_this_year = birthday.replace(year=today.year, day=28)

            # If the birthday has already passed this year,
            # check the next year
            if birthday_this_year < today:
                try:
                    birthday_this_year = birthday.replace(year=today.year + 1)
                except ValueError:
                    birthday_this_year = birthday.replace(year=today.year + 1, day=28)

            days_until_birthday = (birthday_this_year - today).days

            # Current day + the following 6 days = 7 days
            if 0 <= days_until_birthday < days:
                congratulation_date = birthday_this_year

                # Saturday -> Monday
                if congratulation_date.weekday() == 5:
                    congratulation_date += timedelta(days=2)

                # Sunday -> Monday
                elif congratulation_date.weekday() == 6:
                    congratulation_date += timedelta(days=1)

                upcoming_birthdays.append(
                    {
                        "name": record.name.value,
                        "congratulation_date": congratulation_date.strftime("%Y.%m.%d"),
                    }
                )

        upcoming_birthdays.sort(key=lambda item: item["congratulation_date"])

        return upcoming_birthdays


# endregion


# region --- Bot functions ---


def input_error(func):
    """Декоратор для обробки помилок введення користувача(ValueError, IndexError, KeyError)."""

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except ValueError as error:
            return str(error)

        except IndexError:
            return "Enter the argument for the command."

        except KeyError:
            return "Contact not found."

    return inner


def parse_input(user_input):
    """Parse user intput into command and arguments."""

    parts = user_input.strip().split()

    if not parts:
        return ("",)

    command, *args = parts

    return command.lower(), *args


@input_error
def add_contact(args, book: AddressBook):
    """Adds a contact to the address book."""

    if len(args) < 2:
        raise ValueError("Give me name and phone please.")

    name, phone, *_ = args

    record = book.find(name)

    message = "Contact updated."

    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."

    record.add_phone(phone)

    return message


@input_error
def change_contact(args, book: AddressBook):
    """Changes a contact's phone number."""

    if len(args) < 3:
        raise ValueError("Give me name, old phone and new phone please.")

    name, old_phone, new_phone, *_ = args

    record = book.find(name)

    if record is None:
        raise KeyError

    record.edit_phone(old_phone, new_phone)

    return "Contact updated."


@input_error
def show_phone(args, book: AddressBook):
    """Shows a contact's phone number."""

    if not args:
        raise IndexError

    name, *_ = args

    record = book.find(name)

    if record is None:
        raise KeyError

    if not record.phones:
        return "No phone numbers found."

    return "; ".join(phone.value for phone in record.phones)


@input_error
def show_all(book: AddressBook):
    """Return all saved contacts"""

    if not book.data:
        return "No contacts found."

    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    """Adds a birthday to the contact."""

    if len(args) < 2:
        raise ValueError("Give me name and birthday in DD.MM.YYYY format please.")

    name, birthday, *_ = args

    record = book.find(name)

    if record is None:
        raise KeyError

    record.add_birthday(birthday)

    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    """Shows a contact's birthday."""

    if not args:
        raise IndexError

    name, *_ = args

    record = book.find(name)

    if record is None:
        raise KeyError

    if record.birthday is None:
        return "Birthday not found."

    return record.birthday.value.strftime("%d.%m.%Y")


@input_error
def birthdays(args, book: AddressBook):
    """Shows birthdays that will occur during the next week."""

    if args:
        raise ValueError("The birthdays command does not take arguments.")

    upcoming_birthdays = book.get_upcoming_birthdays()

    if not upcoming_birthdays:
        return "No upcoming birthdays."

    return "\n".join(
        f"{item['name']}: {item['congratulation_date']}" for item in upcoming_birthdays
    )


@input_error
def hello_command():
    """Handle hello command."""

    return "How can I help you?"


@input_error
def close_command():
    """Handles close command"""

    return "Good bye!"


def invalid_command():
    """Return a message for an unknown command."""

    return "Invalid command."


# endregion


# region --- Main function ---


def main():
    """Run the assistant bot loop."""

    book = AddressBook()

    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command: ")

        command, *args = parse_input(user_input)

        if command in ("close", "exit"):
            print(close_command())
            break

        elif command == "hello":
            print(hello_command())

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print(invalid_command())


if __name__ == "__main__":
    main()

# endregion
    