# AI ছবি Auto Facebook Poster (GitHub Actions)

এই সেটআপ সম্পূর্ণ ক্লাউডে চলে — আপনার ফোন বা কম্পিউটার চালু রাখার প্রয়োজন নেই।
GitHub-এর নিজের সার্ভার নির্দিষ্ট বিরতিতে (ডিফল্ট প্রতি ৬ ঘণ্টা) এই স্ক্রিপ্ট চালাবে,
যা AI দিয়ে একটা ছবি ও caption বানিয়ে আপনার Facebook Page-এ পোস্ট করে দেবে।

## ধাপ ১: GitHub Repository বানান

1. [github.com](https://github.com)-এ একটা ফ্রি অ্যাকাউন্ট বানান (যদি না থাকে)।
2. উপরে ডানদিকে **+** আইকনে ক্লিক করে **New repository** নির্বাচন করুন।
3. একটা নাম দিন (যেমন `facebook-auto-post`), **Public** বা **Private** যেকোনোটা বেছে নিতে পারেন, তারপর **Create repository**।

## ধাপ ২: ফাইলগুলো আপলোড করুন

এই zip-এ ৩টা ফাইল আছে:

```
post_to_facebook.py
requirements.txt
.github/workflows/auto-post.yml
```

**গুরুত্বপূর্ণ:** `.github/workflows/` ফোল্ডার স্ট্রাকচারটা ঠিক রাখতে হবে, কারণ GitHub ঠিক এই
লোকেশন থেকেই workflow ফাইল খুঁজে নেয়।

আপলোড করার জন্য:
1. আপনার repository-র পেজে যান।
2. **Add file → Upload files** চাপুন।
3. zip ফাইলটা extract করে ভেতরের সব ফাইল ও ফোল্ডার টেনে এনে ছেড়ে দিন (drag & drop), যাতে
   `.github/workflows/auto-post.yml` ফাইলটা ঠিক ওই path-এই থাকে।
4. নিচে **Commit changes** চাপুন।

## ধাপ ৩: Secrets যুক্ত করুন (Token, Page ID, Topic)

1. Repository-র উপরে **Settings** ট্যাবে যান।
2. বামদিকে **Secrets and variables → Actions** নির্বাচন করুন।
3. **New repository secret** চেপে নিচের প্রতিটা একে একে যুক্ত করুন:

| Name | Value |
|---|---|
| `FB_PAGE_TOKEN` | আপনার Facebook Page Access Token |
| `FB_PAGE_ID` | আপনার Facebook Page ID |
| `TOPIC` | যেমন: `প্রকৃতি`, `motivational quotes`, `street food` |
| `STYLE` | (ঐচ্ছিক) যেমন: `photorealistic, DSLR photography, 8k resolution` |

**⚠️ Token নিয়ে সতর্কতা:** Facebook-এর সাধারণ Token কয়েক ঘণ্টার মধ্যে মেয়াদ শেষ হয়ে যায়।
এই automation মাসের পর মাস চলতে থাকার জন্য **long-lived Page Access Token** ব্যবহার করতে হবে
(এটা সাধারণত মেয়াদ শেষ হয় না, যতদিন আপনি Page-এর অ্যাডমিন থাকেন)। Token expire হয়ে গেলে
পোস্ট ব্যর্থ হবে এবং নতুন Token দিয়ে এই Secret আপডেট করতে হবে।

## ধাপ ৪: টেস্ট করুন

1. Repository-র **Actions** ট্যাবে যান।
2. বামদিকে **Auto Facebook Post** workflow-তে ক্লিক করুন।
3. ডানদিকে **Run workflow** বাটন চেপে ম্যানুয়ালি একবার চালান।
4. কয়েক সেকেন্ড পর রান-এর উপর ক্লিক করে লাইভ লগ দেখুন — সব ঠিক থাকলে আপনার Facebook Page-এ
   ছবি পোস্ট হয়ে যাবে।

## এরপর থেকে যা হবে

টেস্ট ঠিকঠাক হলে আর কিছু করতে হবে না। এই workflow নিজে থেকেই প্রতি ৬ ঘণ্টায় চলবে এবং
আপনার দেওয়া টপিক থেকে AI নতুন prompt, ছবি ও caption বানিয়ে Facebook-এ পোস্ট করতে থাকবে —
সম্পূর্ণ স্বয়ংক্রিয়ভাবে, কোনো ডিভাইস চালু রাখা ছাড়াই।

## বিরতি বদলাতে চাইলে

`.github/workflows/auto-post.yml` ফাইলে এই লাইনটা খুঁজুন:

```yaml
- cron: '0 */6 * * *'
```

এটা GitHub repo-র ভেতরে সরাসরি এডিট করা যায় (পেন্সিল আইকনে ক্লিক করে)। cron সময় **UTC**
হিসেবে গণনা হয়, বাংলাদেশ সময় থেকে ৬ ঘণ্টা পিছিয়ে। যেমন প্রতি ৩ ঘণ্টায় চালাতে চাইলে
`0 */3 * * *` লিখুন।

## খরচ ও সীমা

- **Public repository**-তে GitHub Actions সম্পূর্ণ ফ্রি, কোনো মাসিক সীমা নেই।
- **Private repository**-তে ফ্রি প্ল্যানে মাসে ২০০০ মিনিট ফ্রি — এই স্ক্রিপ্ট প্রতি রানে
  মাত্র কয়েক সেকেন্ড সময় নেয়, তাই এই সীমার মধ্যেই অনায়াসে চলবে।
