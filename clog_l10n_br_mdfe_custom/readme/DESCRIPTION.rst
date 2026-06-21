This module makes filling out the MDF-e document easier:

* Fill the modal vehicle information based on a selected `fleet.vehicle`.
* Fill the driver information based on a selected `res.partner` with tms_type is driver.
* Fill the modal body vehicle also based on a selected `fleet.vehicle`.
* Compute the number of NF-e documents is related to the CT-e documents related to the MDF-e.
* Compute the total freight value for each CT-e related to the MDF-e based on the inconterm of the of the CT-e.
* Compute the total freight value for endorsement based on the insurance policy of the partner related to the CT-e.
* Add risk management information fields in the driver's (`res.partner`) model and views.
