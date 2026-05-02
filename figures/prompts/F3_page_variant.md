# F3: Web Page Variant Example (Before/After)

## Background Context (给 GPT 的研究背景)

```
RESEARCH CONTEXT:

This is Figure 3 for a CHI 2027 paper. It's the "intuition figure" — it makes the abstract concept of "accessibility manipulation" concrete and visceral for reviewers who may not be familiar with web accessibility or AI agents.

THE KEY INSIGHT THIS FIGURE MUST COMMUNICATE:
A web page can LOOK completely identical to a human viewer but have a completely different underlying semantic structure. Our "Low" variant removes all semantic HTML (landmarks, headings, links) and replaces them with generic <div> and <span> elements — but preserves the visual CSS styling. The page looks the same, but an AI agent reading the accessibility tree sees a flat, meaningless list of generic elements instead of a structured document.

CONCRETE EXAMPLE (Magento e-commerce storefront):
- BASE page has: <nav> with links, <main> with <h1> product title, <button> for Add to Cart, <a href> for navigation
- LOW variant has: <div> with <span onclick> instead of links, <div style="font-size:2em"> instead of <h1>, generic containers everywhere
- HIGH variant has: everything from Base PLUS aria-labels on images, skip-nav link, landmark roles explicitly declared

WHAT THE AI AGENT "SEES":
- Base a11y tree: "banner → navigation → main → heading 'Olivia Jacket' → link 'Home' → button 'Add to Cart'"
- Low a11y tree: "RootWebArea → generic → generic → generic → generic → generic → generic..."
  (The agent has NO structural information — it's like reading a book with all chapter titles removed)
- High a11y tree: Same as Base but with additional labels and landmarks

WHY THIS MATTERS:
- 96.3% of real websites have accessibility violations (WebAIM 2024)
- Our Low variant models the WORST 83.3% of real sites (validated via ecological audit of 34 sites)
- AI agents that rely on the accessibility tree (which is ALL text-based agents) are catastrophically affected
- The visual appearance is unchanged — this is NOT about broken pages, it's about broken SEMANTICS

THIS FIGURE should make a CHI reviewer think: "Oh! The page looks fine but the agent is blind. That's the whole point of the paper."
```

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (3:2 aspect ratio, 2400×1600px). This is Figure 3 for a CHI 2027 paper about web accessibility and AI agents.

The figure shows the SAME web page under three accessibility conditions, demonstrating that visual appearance is preserved while semantic structure is destroyed.

Title at top (bold, 12pt): "Same Visual Appearance, Different Semantic Structure"
Subtitle (italic, 9pt): "An e-commerce product page under Base, Low (degraded), and High (enhanced) accessibility variants"

═══ LAYOUT: Three browser window mockups arranged horizontally ═══

Each "window" has:
- A simplified browser chrome at top (gray bar with dots for close/minimize/maximize, address bar showing "http://store.example.com/product/jacket")
- The page content below
- An annotation strip below the window

All three windows show the EXACT SAME visual page content (this is critical — they must look identical visually).

═══ PAGE CONTENT (same in all three windows): ═══

A simplified but realistic e-commerce product page:
- Top bar: navigation with "Home | Women | Men | Gear | Sale" links (blue text, underlined)
- Below: breadcrumb "Home > Women > Tops > Jackets" (small gray text)
- Left side: product image placeholder (a teal/green jacket illustration or gray rectangle labeled "Product Image")
- Right side:
  - Product title "Olivia 1/4 Zip Light Jacket" (large, bold)
  - Price "$77.00" (medium, dark)
  - Rating "★★★★☆ 3 Reviews" (gold stars)
  - Size buttons: "XS  S  M  L  XL" (small rounded buttons)
  - Large blue button "ADD TO CART"
- Bottom: tab bar "Details | More Information | Reviews (3)"

═══ WINDOW 1 (left): "Base (unmodified)" ═══

- Green label above window: "BASE"
- Page content as described above (clean, no annotations)
- Below window, in a light green box:
  "✓ Semantic HTML preserved"
  "<nav> <main> <h1> <a href> <button>"
- Small code snippet showing the a11y tree:
  "banner → navigation → main → heading 'Olivia...' → link 'Home' → button 'Add to Cart'"

═══ WINDOW 2 (center): "Low variant (L1+L6+L11)" ═══

- Red label above window: "LOW (degraded)"
- SAME visual page content (identical appearance!)
- But with semi-transparent RED OVERLAY ANNOTATIONS showing DOM changes:
  - Red strikethrough near nav area: "<nav> → <div>"
  - Red strikethrough near title: "<h1> → <div style='font-size:2em'>"
  - Red strikethrough near links: "<a href='...'> → <span onclick='...'>"
  - Red badge in corner: "SSIM = 0.99 (visually identical)"
- Below window, in a light red box:
  "✗ Semantic structure destroyed"
  "<div> <div> <span onclick> <div>"
- Small code snippet showing the a11y tree:
  "RootWebArea → generic → generic → generic → generic → generic..."
- Annotation arrow pointing to the a11y tree: "Agent sees: flat, meaningless list"

═══ WINDOW 3 (right): "High variant (H1-H8)" ═══

- Green label above window: "HIGH (enhanced)"
- SAME visual page content (identical appearance!)
- But with semi-transparent GREEN OVERLAY ANNOTATIONS showing enhancements:
  - Green "+" near nav: "+role='navigation' aria-label='Main menu'"
  - Green "+" near image: "+alt='Olivia 1/4 Zip Light Jacket, teal'"
  - Green "+" at very top: "+Skip to main content (visually hidden link)"
  - Green "+" near size buttons: "+aria-label='Size: Small'"
- Below window, in a light green box:
  "✓ Enhanced accessibility"
  "<nav aria-label> <main> <h1> <img alt> <button aria-label>"
- Small code snippet showing the a11y tree:
  "banner 'Main menu' → navigation → main → heading 'Olivia...' → img 'Olivia Jacket, teal' → button 'Add to Cart'"

═══ BOTTOM STRIP (spanning full width): ═══

A comparison callout box with light yellow background:
"KEY INSIGHT: All three pages look identical to a human user (SSIM > 0.99).
But the AI agent's 'view' (accessibility tree) ranges from rich semantic structure (Base/High) to a flat list of generic elements (Low).
This is the mechanism by which accessibility degradation causes agent failure."

═══ STYLE ═══
- White background
- Browser windows should look like simplified real browser windows (thin gray chrome)
- The page content inside should look like a real (simplified) e-commerce page
- The RED annotations on the Low window should be semi-transparent overlays (not obscuring the page)
- The GREEN annotations on the High window similarly
- The visual IDENTITY between all three windows is the most important thing — they must look the same
- Clean, academic, no excessive decoration
- All text legible at print size
- Similar to "before/after" comparison figures in HCI papers
```

## Iteration Guidance
- THE MOST IMPORTANT THING: all three windows must look visually identical. The annotations are overlays, not changes to the page itself.
- If the page content is too complex, simplify (fewer elements, just nav + title + button)
- The a11y tree snippets below each window are the "punchline" — make them prominent
- The "SSIM = 0.99" badge on the Low window is crucial — it proves visual identity
- If GPT struggles with the overlay annotations, try: "Show the annotations as callout boxes with arrows pointing to specific page elements, positioned outside the browser window"
- Alternative approach: instead of browser mockups, show the a11y tree TEXT side-by-side (3 columns of monospace text). Less pretty but more accurate.
