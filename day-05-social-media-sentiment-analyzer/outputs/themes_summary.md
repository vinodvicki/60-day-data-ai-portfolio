# Day 05 — Top-theme summary

1,462 analysed comments. A comment can carry up to 2 themes, so theme
shares sum to over 100%. Sentiment splits are as classified by our
rule-based model — not ground truth. Excerpts are short (≤120 chars),
author names omitted.

## Themes

| Theme | Comments | Share | Positive | Neutral | Negative |
|---|---|---|---|---|---|
| Other (no theme matched) | 862 | 59.0% | 22.0% | 71.7% | 6.3% |
| Praise | 329 | 22.5% | 91.2% | 4.9% | 4.0% |
| Career | 144 | 9.8% | 40.3% | 54.2% | 5.6% |
| Tutorial quality | 116 | 7.9% | 70.7% | 17.2% | 12.1% |
| Price / cost | 38 | 2.6% | 47.4% | 44.7% | 7.9% |
| Questions | 33 | 2.3% | 21.2% | 66.7% | 12.1% |
| Audio / video | 29 | 2.0% | 62.1% | 27.6% | 10.3% |
| Humour | 27 | 1.8% | 63.0% | 25.9% | 11.1% |
| Criticism | 21 | 1.4% | 42.9% | 9.5% | 47.6% |
| Requests | 5 | 0.3% | 20.0% | 80.0% | 0.0% |

### Other (no theme matched) — 862 (59.0%)

The fixed lists missed the large Google Data Analytics course-cohort
check-in pattern. Reported, not re-tuned.

- "JUst going to say that mayonaisse looked weird."
- "Not even 2nd week😅boom...I'm here.."
- "From Coursera. almost completed my course 1. lesssgooooo"

### Praise — 329 (22.5%)

- "Hi, who else is here from the Google analytics course? It's fun... I'm from Nigeria... Nice to meet you"
- "Awesome topics...midukiiiiii....."
- "VERY HELPFUL THNKS"

### Career — 144 (9.8%)

- "Starts at 12:55 😪"
- "I can’t believe how helpful this was, amazing job!"
- "Just starting the GDA certification, and I'm glad there's already a tradition on this video lol. It's really good!"

### Tutorial quality — 116 (7.9%)

- "Well detailed and straightforward! Thank you!"
- "This was masterfully explained, phenomenal job!"
- "This video has completely transformed my understanding!"

### Price / cost — 38 (2.6%)

- "All this talk about some course lol, im just happy i didnt pay for something i could watch for free on Youtube"
- "You putting this up for free is actually clutch - praise to you"
- "better use UNION ALL for the list of money earned and spent"

### Questions — 33 (2.3%)

- "thank you for the course,how do i download the excercise files?"
- "Could you please help me out? The zip file isn't working"
- "why you ignored the N:M table for branch and branch_supplier?"

### Audio / video — 29 (2.0%)

- "Thank you so much for providing this high quality content for free, i cannot express my gratitude enough."
- "bruh what are these captions 2:32:56 lmao"
- "The production quality is worth sharing I will definitely recommend this."

### Humour — 27 (1.8%)

- "Just starting the GDA certification, and I'm glad there's already a tradition on this video lol. It's really good!"
- "All this talk about some course lol, im just happy i didnt pay for something i could watch for free on Youtube"
- "Here from the Google Data Analytics course on Coursera 😂. Who else is doing this in 2026?"

### Criticism — 21 (1.4%)

- "uploaded 7 years ago? jesus. i feel like this course is really outdated. probably we are entering too late."
- "can data analytics be used to help a new business predict possible mistakes from other business like a startup"
- "Ts is boring, i wanted to learn SQL and practical stuff, i don't care about this corporate bootlicking culture"

### Requests — 5 (0.3%)

- "Hello!! Please make the audio available in Portuguese! PLEASE"

## Top words and bigrams per sentiment class (as classified by the model)

Stopwords removed; "data", "analytics", "google" kept (they are content
here, not stopwords). Counts are occurrences across comments in the class.

### Positive (n=594)

Top words: data 139, analytics 97, google 92, thank 61, good 54, i'm 47,
better 43, best 41, great 41, thanks 39, every 37, ai 34, amazing 31,
helpful 31, easy 29, made 28, understand 28, content 27, learn 26,
clear 25.

Top bigrams: data analytics 87, google data 78, easy follow 22,
enjoyed every 21, every second 21, clear easy 20, deserves recognition 17,
appreciate effort 16, good luck 16, helped understand 15,
understand better 14, day better 13, come back 12, made day 12,
production quality 12, data analyst 11, top notch 11,
analytics wishing 10, back watch 10, definitely recommend 10.

### Neutral (n=769)

Top words: data 119, analytics 94, google 90, ai 39, i'm 34, please 32,
starting 27, made 25, well 24, anyone 22, october 22, que 22, t 22,
deserves 21, know 21, today 20, years 20, back 19, come 19, watching 19.

Top bigrams: data analytics 76, google data 69, google analytics 17,
data analysis 15, come back 13, definitely recommend 12, deserves views 12,
starting today 11, back watch 10, data analyst 10, top notch 9,
well made 8, worth sharing 8, years ago 8, i'm google 7, april google 6,
well well 6, analytics coursera 5, analytics student 5,
deserves recognition 5.

Note: "que" (Spanish slipping through the Latin-script language filter)
and "t" (curly-apostrophe tokenisation splitting "don't") are known
artefacts of the baseline — see README Limitations.

### Negative (n=99)

Top words: ai 25, good 15, data 10, hidden 10, human 10, time 10,
understand 10, every 9, humans 9, it's 9, layer 9, never 9, because 8,
don't 7, intelligence 7, neuron 7, real 7, t 7, analytics 6, doesn't 6.

Top bigrams: expect good 6, data analytics 5, hidden layer 4,
layer neurons 4, answers internet 3, doesn t 3, hidden layers 3,
high value 3, made expect 3, never learnt 3, search answers 3,
well made 3, ai cannot 2, artificial intelligence 2, cannot go 2,
differentiator standard 2, disciplined feedback 2, doesn't search 2,
every aspect 2, exact opposite 2.

Note: negative-class bigrams are dominated by content words from the
3Blue1Brown neural-network video ("hidden layer", "layer neurons") —
the lexicon scores words, not intent, and cannot tell a technical
term from a complaint.
