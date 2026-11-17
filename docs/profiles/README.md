# Writing a profile

A profile tells the pilot how to operate one desktop program through its own user interface. It is a description,
not a copy of the program. Every profile keeps these rules.

1. **Own words only.** Describe the steps in your own words. Never copy text from the program's manual or its
   documentation into a profile.
2. **UI only.** Use only what the program's windows show. Never read the program's data files, and never reverse
   engineer or patch it.
3. **Read back every write.** After a write, read the value back from the program's own list to confirm it.
4. **Back up before a write run.** Keep a backup the program itself can restore from.
5. **No real data in the repo.** Profiles, examples and tests use fictitious data only. Never commit a customer's
   records, names or identifiers.
6. **Respect the program's notices.** Never remove or cover a copyright notice.

A profile drives the user's own licensed program on the user's own machine. It adds no user and transfers no licence.
