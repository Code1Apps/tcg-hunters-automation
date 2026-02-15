const fs = require('fs');
require('dotenv').config();
const path = require('path');
const fetch = require('node-fetch');
const cheerio = require('cheerio');
const ApiRepo = require('./repo/api.repo');

const GLOBAL_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
};


async function main() {
  const outDir = path.resolve(__dirname, '..', 'outputs');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const apiRepo = new ApiRepo();
  const task = await apiRepo.getExpansionNewCardsTask("pokemon");

  if (!task) {
    console.log('No tasks available to process.');
    return;
  }
  const URL = 'https://bulbapedia.bulbagarden.net/wiki/' + task.expansion.name.replaceAll(" ", "_") + '_(TCG)';

  console.log('Fetching', URL);
  const res = await fetch(URL, { headers: GLOBAL_HEADERS });
  const text = await res.text();
  console.log('Response Http Code:', res.status);

  if (res.status !== 200) {
    console.error('Non-200 response, aborting parse');
    return;
  }

  const $ = cheerio.load(text);

  // find the table with class 'roundy'
  let numberCol = $('th:contains("No.")')
  if (!numberCol || numberCol.length === 0) {
    numberCol = $('th:contains("no.")')
  }
  if (!numberCol || numberCol.length === 0) {
    console.error('Could not find table.roundy on page');
    return;
  }

  let headersRow = numberCol.parent();
  let dataRows = numberCol.parent("tr").nextAll('tr')

  // find header row: a <th> that contains 'No' or 'Number', otherwise first <tr> with <th>
  let colMap = {};
  $(headersRow).find('th').each((i, el) => {
    if ($(el).css('display') === 'none') return;
    const txt = $(el).text().trim().toLowerCase();
    if (txt.includes('no') || txt.includes('number')) colMap.number = i;
    else if (txt.includes('name') || txt.includes('card')) colMap.name = i;
    else if (txt.includes('rarity')) colMap.rarity = i;
    else if (txt.includes('promo') || txt.includes('promotion')) colMap.promotion = i;
    else if (txt.includes('type')) colMap.type = i;
  });


  const cards = [];
  const existingCards = task.newCards?.map((card) => card.number) ?? [];
  for (let i = 0; i < dataRows.length; i++) {
    const tr = dataRows[i];
    const cols = $(tr).find('td:visible,th:visible');
    if (cols.length === 0) continue; // skip non-data rows

    let card = {
      number: '',
      rarity: '',
      image: '',
      name: [],
      type: [],
      promotion: [],
      imageName: '',
    };
    if (colMap.number !== undefined) card.number = $(cols[colMap.number]).text().trim().replace('—', '');
    if (colMap.rarity !== undefined) card.rarity = $(cols[colMap.rarity]).text().trim().replaceAll('—', '');

    if (colMap.name !== undefined && $(cols[colMap.name]).length > 0) {
      card.name = $(cols[colMap.name]).html().split('<br>').map((el) => $(el).text().trim()).filter((el) => el.length > 0);
      card.imageName = $(cols[colMap.name]).find('a').first().attr('href')?.match(/\(([^)]+)\)/)[1];
      if (card.imageName) {
        card.imageName = (card.name[0] + "" + card.imageName).replaceAll("_", "") + ".jpg"
      }
    }

    if (colMap.promotion !== undefined && $(cols[colMap.promotion]).length > 0) {
      card.promotion = $(cols[colMap.promotion]).html().trim().split('<br>').map((el) => $("<p>" + el + "</p>").text().trim());
    }

    if (colMap.type !== undefined && $(cols[colMap.type]).length > 0) {
      let imgs = $(cols[colMap.type]).find('img');
      if (imgs.length > 0) {
        card.type = imgs.map((i, el) => $(el).attr("alt").trim().toLowerCase()).get();
      }
    }

    // Ignore cards with missing number or name
    if (!card.number || card.name.length === 0) {
      // console.log('Skipping invalid card:', JSON.stringify(card));
      continue;
    }

    if (existingCards.includes(card.number) || (task.expansion && task.expansion.cards && task.expansion.cards.includes(card.number))) {
      continue;
    }

    cards.push(card);
  }

  // Fetch and download images for valid cards
  const imgDir = path.resolve(__dirname, '..', 'public', 'img', 'tmp');
  if (!fs.existsSync(imgDir)) fs.mkdirSync(imgDir, { recursive: true });

  console.log(`Downloading images for ${cards.length} cards...`);
  for (const card of cards) {
    if (card.imageName) {
      try {
        const fileTitle = `File:${card.imageName}`;
        const apiUrl = `https://archives.bulbagarden.net/w/api.php?action=query&titles=${fileTitle}&prop=imageinfo&iiprop=url&format=json`;

        const res = await fetch(apiUrl, { headers: GLOBAL_HEADERS });

        if (res.status === 200) {
          const data = await res.json();
          const pages = data?.query?.pages;
          if (pages) {
            const pageId = Object.keys(pages)[0];
            const pageData = pages[pageId];
            if (pageData && pageData.imageinfo && pageData.imageinfo.length > 0) {
              const imageUrl = pageData.imageinfo[0].url;

              // Download the image
              const imageRes = await fetch(imageUrl, { headers: GLOBAL_HEADERS });
              if (imageRes.ok) {
                const buffer = await imageRes.buffer();
                const timestamp = Date.now();
                const ext = path.extname(imageUrl) || '.jpg';
                const filename = `${timestamp}${ext}`;
                const filepath = path.join(imgDir, filename);

                fs.writeFileSync(filepath, buffer);
                card.image = process.env.AUTO_URL + '/img/tmp/' + filename; // Store filename instead of URL
                console.log(`Downloaded: ${filename}`);
              }
            }
          }
        }
        await new Promise(resolve => setTimeout(resolve, 500)); // Delay to respect rate limits
      } catch (err) {
        console.error(`Failed to download image for ${card.imageName}:`, err.message);
      }
    }
  }

  const outJson = path.join(outDir, 'new_cards_pokemon.json');
  fs.writeFileSync(outJson, JSON.stringify(cards, null, 2), { encoding: 'utf8' });
  console.log(`Found ${cards.length} NEW cards. Wrote to: ${outJson}`);

  // Create log entry for this run
  const log = {
    createdAt: new Date().toISOString(),
    type: cards.length > 0 ? 'success' : 'info',
    message: cards.length > 0
      ? `Found and processed ${cards.length} new card(s)`
      : 'No new cards found'
  };

  try {
    console.log(`Updating task ${task.id}...`);
    await apiRepo.updateTask(task.id, cards, [log]);
    console.log('Task updated successfully.');
  } catch (error) {
    console.error('Failed to update task:', error.message);
  }
}

main().catch(err => {
  console.error('Error in scraper:', err);
  process.exit(1);
});
