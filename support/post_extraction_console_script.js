(async function() {
    const MAX_POSTS = 100;
    const MAX_FAILED_SCROLLS = 5;
    const SCROLL_DELAY_MS = 2500;
    
    const collectedPosts = new Map();
    let consecutiveFailedScrolls = 0;
    let lastHeight = document.body.scrollHeight;

    const currentSubMatch = window.location.pathname.match(/\/r\/([^\/]+)/);
    const defaultSubreddit = currentSubMatch ? currentSubMatch[1] : "";

    while (collectedPosts.size < MAX_POSTS && consecutiveFailedScrolls < MAX_FAILED_SCROLLS) {
        const postElements = document.querySelectorAll('shreddit-post, article, div[data-testid="post-container"]');
        
        postElements.forEach(el => {
            if (collectedPosts.size >= MAX_POSTS) return;

            let title = "";
            let timestamp = "";
            let subreddit = "";
            let engagement = "";

            if (el.tagName.toLowerCase() === 'shreddit-post') {
                title = el.getAttribute('post-title') || el.querySelector('[slot="title"]')?.innerText || "";
            } else {
                const titleEl = el.querySelector('h3, [data-testid="post-title"], a.title');
                title = titleEl ? titleEl.innerText.trim() : "";
            }
            title = title.replace(/\s+/g, ' ').trim();

            const timeEl = el.querySelector('time');
            timestamp = timeEl ? timeEl.getAttribute('datetime') : "";

            if (el.tagName.toLowerCase() === 'shreddit-post') {
                subreddit = el.getAttribute('subreddit') || el.getAttribute('data-subreddit') || "";
            }
            if (!subreddit) {
                const subLink = el.querySelector('a[href^="/r/"], a[href*="/r/"]');
                if (subLink) {
                    const match = subLink.getAttribute('href').match(/\/r\/([^\/]+)/);
                    if (match) subreddit = match[1];
                }
            }
            if (!subreddit) {
                subreddit = defaultSubreddit;
            }
            subreddit = subreddit.replace(/^r\//, '');

            if (el.tagName.toLowerCase() === 'shreddit-post') {
                engagement = el.getAttribute('score') || "";
            } else {
                const scoreEl = el.querySelector('[id*="vote-score"], [data-testid="post-score"]');
                engagement = scoreEl ? scoreEl.innerText.trim() : "";
            }

            if (title && !collectedPosts.has(title)) {
                collectedPosts.set(title, {
                    text: title,
                    timestamp: timestamp || "",
                    subreddit: subreddit || "",
                    engagement: engagement || ""
                });
            }
        });

        if (collectedPosts.size >= MAX_POSTS) {
            break;
        }

        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, SCROLL_DELAY_MS));

        let newHeight = document.body.scrollHeight;
        if (newHeight === lastHeight) {
            consecutiveFailedScrolls++;
        } else {
            consecutiveFailedScrolls = 0;
            lastHeight = newHeight;
        }
    }

    const finalResults = Array.from(collectedPosts.values()).map((post, index) => ({
        post_id: index + 1,
        ...post
    }));

    const headers = ['post_id', 'text', 'timestamp', 'subreddit', 'engagement'];
    const csvRows = [headers.join(',')];

    finalResults.forEach(row => {
        const values = headers.map(header => {
            const val = row[header] !== null && row[header] !== undefined ? String(row[header]) : '';
            return `"${val.replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join(','));
    });

    const csvString = csvRows.join('\n');
    
    // Prepend UTF-8 BOM (\uFEFF) to guarantee correct character decoding in spreadsheet software
    const blob = new Blob(['\uFEFF' + csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const downloadLink = document.createElement('a');
    downloadLink.href = url;
    downloadLink.download = `reddit_posts_${defaultSubreddit || 'export'}.csv`;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
})();