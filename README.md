### Requirements: 
Python 3.9 or newer. No packages are required.

1. Put main.py, models.py, enums.py, and services.py in the same folder.
2. From that folder, run python3 main.py, python main.py, or py main.py (depending on OS and install).
3. On first launch, there are no existing accounts, so select Register. EventApprover & SystemAdministrator open the admin menu, and all other users open the standard menu. Log in with the email you registered with.
4. Enter dates as YYYY-MM-DD HH:MM and facility hours as HH:MM. Bookings must start in the future (from time of use) and fit within facility hours. A default facility is generated, Curtis Laws Wilson Library, which has opening and closing hours from 8:00 to 22:00 by default. Use 24 hour time format.
5. Data is saved to users.json in the same folder when you choose Log Out or Exit. Delete users.json to start fresh.
