const puppeteer = require("puppeteer");


// Helper: read stdin fully
const getStdin = async () => {
    const chunks = [];
    for await (const chunk of process.stdin) {
        chunks.push(chunk);
    }
    return Buffer.concat(chunks).toString('utf-8');
};

(async () => {
    const json = await getStdin();

    const data = JSON.parse(json);   // parse stdin JSON
    const canvasJson = data.canvas_content; // actual Fabric JSON
    const canvasWidth = 950;
    const canvasHeight = 800;


    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/chromium', // or '/snap/bin/chromium'
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Minimal HTML with Fabric.js
    await page.setContent(`
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    </head>
    <body>
      <canvas id="c"></canvas>
      <script>
        window.fabricCanvas = new fabric.Canvas('c', {
          width: ${canvasWidth},
          height:  ${canvasHeight},
          backgroundColor: '#F4F4F4'
        });
        
        window.reorderAlwaysOnTop = function() {
          const objs = window.fabricCanvas.getObjects();
          objs.forEach(obj => {
            if (obj.alwaysOnTop) {
              const idx = window.fabricCanvas._objects.indexOf(obj);
              if (idx > -1) {
                window.fabricCanvas._objects.splice(idx, 1);
                window.fabricCanvas._objects.push(obj);
              }
            }
          });
          window.fabricCanvas.renderAll();
        };

        // Hook: whenever a new object is added, re‑push flagged one
        window.fabricCanvas.on('object:added', () => {
          window.reorderAlwaysOnTop();
        });

        window.exportAsImage = function() {
          const exportWidth = 950;
          const exportHeight = 800;

          const canvasWidth = window.fabricCanvas.getWidth();
          const canvasHeight = window.fabricCanvas.getHeight();

          const scaleX = exportWidth / canvasWidth;
          const scaleY = exportHeight / canvasHeight;
          const scale = Math.min(scaleX, scaleY);

          window.fabricCanvas.getObjects().forEach(obj => {
            obj.scaleX *= scale;
            obj.scaleY *= scale;
            obj.left *= scale;
            obj.top *= scale;
            obj.setCoords();
          });

          window.fabricCanvas.renderAll();

          const dataUrl = window.fabricCanvas.toDataURL({
            format: 'png',
            quality: 1,
            width: exportWidth,
            height: exportHeight,
            multiplier: 1
          });

          // restore
          window.fabricCanvas.getObjects().forEach(obj => {
            obj.scaleX /= scale;
            obj.scaleY /= scale;
            obj.left /= scale;
            obj.top /= scale;
            obj.setCoords();
          });
          window.fabricCanvas.setWidth(canvasWidth);
          window.fabricCanvas.setHeight(canvasHeight);
          window.fabricCanvas.renderAll();
          
          

         
          return dataUrl;
        };
      </script>
    </body>
    </html>
  `);

    // Load JSON into canvas
    await page.evaluate((canvasJson) => {
        return new Promise(resolve => {
            window.fabricCanvas.loadFromJSON(canvasJson, () => {
                window.fabricCanvas.requestRenderAll();
                resolve();
            });
        });
    }, canvasJson);


    // Export image
    const dataUrl = await page.evaluate(() => window.exportAsImage());

    const base64Data = dataUrl.replace('data:image/png;base64,', '');

    const imgBuffer = Buffer.from(base64Data, 'base64');

    process.stdout.write(imgBuffer);

    await browser.close();
})();
