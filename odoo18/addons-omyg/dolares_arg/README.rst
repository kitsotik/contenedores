===========
Dolares Argentina
===========
.. |badge1| image:: https://img.shields.io/badge/maturity-Stable-brightgreen
    :target: https://odoo-community.org/page/development-status
    :alt: Stable
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://onlyone.odoo.com/web/image/website/1/logo/OnlyOne%20Soft?unique=dccda5b
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
|badge1| |badge2| |badge3|

This module extends the functionality of Odoo's accounting module to fetch and update Argentine dollar exchange rates from the DolarAPI (https://dolarapi.com) and Banco Nación Argentina (BNA) website. It creates specific currencies for each dollar type (e.g., USB for Blue, USO for Official) and updates their rates daily via a scheduled action. Users can configure which dollar types to fetch in the accounting settings.

**Table of contents**
.. contents::
   :local:

Install
=======
To install this module, you need to:

1. Install the required Python dependencies:
   - `requests`: For making HTTP requests to the DolarAPI.
   - `bs4` (BeautifulSoup4): For scraping the BNA website.
   You can install them using pip:
   .. code-block:: bash
       pip install requests bs4
2. Add the module to your Odoo addons path.
3. Update the Odoo module list and install the `dolares_arg` module.

Configure
=========
To configure this module, you need to:

1. Go to *Settings > Accounting*.
2. Under the "Dólares Argentina" section, select the dollar types you want to fetch and update automatically (e.g., Oficial, Blue, BNA, etc.).
3. Save the configuration. The module will automatically create the corresponding currencies (e.g., USB for Blue, USO for Oficial) if they do not exist and update their rates daily via a scheduled action.

Usage
=====
1. Ensure the desired dollar types are enabled in *Settings > Accounting*.
2. The module automatically fetches rates daily via a scheduled action (cron).
3. Check the rates in *Accounting > Configuration > Currencies* under the respective currency codes (e.g., USB, USO, USBN).
4. If an error occurs (e.g., API or scraping failure), check the logs in *Settings > Technical > Logs*.

Known issues / Roadmap
======================
* The BNA website structure may change, requiring updates to the scraping logic.
* Future versions may include support for additional dollar sources or configurable rate calculation methods.

Bug Tracker
===========
For issues, please contact Be OnlyOne at https://onlyone.odoo.com/contactus.

Credits
=======
Authors
~~~~~~~
* Be OnlyOne

Contributors
~~~~~~~~~~~~
* `Be OnlyOne <https://onlyone.odoo.com/>`_

  * Matías Bressanello

Maintainers
~~~~~~~~~~~
This module is maintained by Be OnlyOne.