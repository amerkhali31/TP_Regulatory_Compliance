1. reporting not matching liability is the most sever error
   - it is usually caused by one of the following
     - an item being barked as non taxable when in reality it should have been
     - an item not having a unit associated to it
     - purchases made by a wholesaler are not supposed to count towards liability
2. something goes wrong with the customer list that causes it to not correctly read the address, city, state, zip
   - i have not yet pinned down a cause for this.
   - some suspected causes that are not verified are duplicate customer names or missing comma
   - nonetheless, if the address exists in the customers workbook but didnt get correctly added to the tp 1 il report, those should be automatically added to the report
3. brand family spelled wrong leading to missing manufacturer name
   - find the closest match and automatically assign it
