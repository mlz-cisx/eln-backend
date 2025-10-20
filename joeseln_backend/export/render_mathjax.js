const puppeteer = require("puppeteer");

(async () => {


  // Read HTML from stdin
  const getStdin = async () => {
    const chunks = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    return Buffer.concat(chunks).toString("utf-8");
  };

  const htmlContent = await getStdin();

  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setContent(htmlContent, { waitUntil: "networkidle0" });


  // Wait for all images to load
  await page.evaluate(async () => {
    const selectors = Array.from(document.images).map(img => {
      if (img.complete) return null;
      return new Promise(resolve => {
        img.addEventListener('load', resolve);
        img.addEventListener('error', resolve); // resolve even if image fails to load
      });
    }).filter(p => p !== null);
    await Promise.all(selectors);
  });


  const pdfBuffer = await page.pdf({ format: "A4" });
  await browser.close();
  process.stdout.write(pdfBuffer);

})();
