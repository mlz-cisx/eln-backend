Integration
=====================

This page documents the third-party frontend libraries integrated into the
ELN application. These services are loaded client-side to provide
data interationn.


.. tip::
   Ideas on integrating other data visualisation services are welcome

Plotly Editor
-------------

.. confval:: Library
   :default: plotly.js-dist-min (Plotly.js)

**Purpose**

Scientists can visualise csv file from instrument it as a
line + markers scatter plot. The plot is interactive: the user can pan,
zoom, hover to inspect data points, and toggle traces on and off. An
optional "Sketch from Plot Image" button exports the current plot view
as a new sketch element in the labbook for annotation.


Video.js Player
---------------

.. confval:: Library
   :default: video.js (Video.js)

**Purpose**

Scientists can view video files attached to labbook entries directly in the
browser, with plaback controls.

3Dmol Molecular Viewer
----------------------

.. confval:: Library
   :default: 3Dmol.js (3Dmol)


**Purpose**

Scientists can view molecular structures from computational chemistry or
crystallography data — in PDB, CIF, or XYZ format — directly in the
labbook. The viewer supports multiple rendering styles and interactive atom
inspection.

