Integration
=====================

This page documents the third-party frontend libraries integrated into the
ELN application. These services are loaded client-side to provide
data integration.


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


HDF5 Viewers (H5Web)
--------------------

.. confval:: Library
   :default: @h5web/app, @h5web/h5wasm (H5Web)

**Purpose**

The ELN integrates two different HDF5 viewers based on the H5Web framework.
Each viewer serves a distinct use case depending on the data source and file
size. Both viewers are embedded directly into the Angular frontend.

**1. WASM-based Viewer (H5WasmBufferProvider)**

This viewer loads HDF5 files directly from a ``File`` object or binary buffer
using the WebAssembly backend. It is ideal for small to medium-sized files
uploaded by the user.


**2. HSDS-based Viewer (HsdsProvider)**

This viewer connects to an HSDS server instance and streams large HDF5/Nexus
datasets over HTTP. It is suitable for very large files or remote datasets
stored on HPC systems. This integration provides a standalone page capable of
rendering extremely large ``.h5`` files without loading them into browser memory.

.. tip::
   The frontend automatically selects the appropriate viewer depending on
   whether the user provides a local file (WASM) or an HSDS URL (remote).

.. note::
   Instructions for setting up an HSDS server can be found in the official
   HSDS repository: https://github.com/HDFGroup/hsds/



