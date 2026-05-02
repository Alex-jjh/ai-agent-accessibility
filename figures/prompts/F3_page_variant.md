# F3: Web Page Variant Example (Before/After)

## Purpose
Intuitive visual showing what a real web page looks like under different
accessibility variants. Makes the abstract "operator" concept concrete
for non-technical reviewers.

## GPT Image 2 Prompt

```
Create a clean academic research paper figure in landscape orientation (16:9, 2560×1440px). White background.

Title: "Example: E-commerce Product Page Under Three Accessibility Variants"

The figure shows THREE browser window mockups side by side, each showing the same product page but with different accessibility states. Each window has a thin gray browser chrome (address bar, tabs) at the top.

═══ LEFT WINDOW: "Base (unmodified)" ═══
- Browser tab: "Luma Store — Product"
- Page content (simplified e-commerce product page):
  - Top: navigation bar with links "Home | Women | Men | Gear | Sale"
  - Below nav: breadcrumb "Home > Women > Tops > Jackets"
  - Main content area:
    - Product image placeholder (gray rectangle with "jacket photo" text)
    - Product title: "Olivia 1/4 Zip Light Jacket"
    - Price: "$77.00"
    - Star rating: "★★★★☆ (3 Reviews)"
    - Size selector buttons: "XS S M L XL"
    - "Add to Cart" button (blue, prominent)
    - Tab section: "Details | More Information | Reviews"
  - Footer with "© Luma Store"
- Below window, annotation: "✓ Semantic HTML: <nav>, <main>, <h1>, <button>, <a href>"
- Green checkmark icon

═══ MIDDLE WINDOW: "Low variant (L1 + L6 + L11 applied)" ═══
- Same visual appearance as Base (this is critical — it LOOKS identical)
- But with RED ANNOTATIONS overlaid showing what changed in the DOM:
  - Red strikethrough on nav area: "❌ <nav> → <div>" (L1)
  - Red strikethrough on product title: "❌ <h1> → <div style='font-size:2em'>" (L6)
  - Red strikethrough on navigation links: "❌ <a href='...'> → <span onclick='...'>" (L11)
  - Red strikethrough on breadcrumb: "❌ <nav aria-label='breadcrumb'> → <div>"
  - Small red label in corner: "SSIM = 0.99 (visually identical)"
- Below window, annotation: "✗ Generic containers: <div>, <span onclick>, no landmarks"
- Red X icon
- Additional note: "Agent sees flat list of 200+ elements with no structural hierarchy"

═══ RIGHT WINDOW: "High variant (H1-H8 applied)" ═══
- Same visual appearance as Base
- But with GREEN ANNOTATIONS overlaid showing enhancements:
  - Green "+" on nav: "+ role='navigation' aria-label='Main menu'"
  - Green "+" on product image: "+ alt='Olivia 1/4 Zip Light Jacket in teal'"
  - Green "+" at top of page: "+ Skip to main content (hidden link)"
  - Green "+" on size buttons: "+ aria-label='Size: Small'"
  - Green "+" on star rating: "+ aria-label='Rating: 4 out of 5 stars'"
- Below window, annotation: "✓ Enhanced: landmarks, labels, skip-nav, alt text"
- Green checkmark icon

═══ BOTTOM STRIP ═══

A horizontal comparison bar showing:
"Agent a11y tree observation:"
- Base: "banner → navigation → main → heading 'Olivia...' → link 'Home' → button 'Add to Cart'"
- Low: "RootWebArea → generic → generic → generic → generic → generic → generic..."
- High: "banner 'Main menu' → navigation → main → heading 'Olivia...' → link 'Home' → button 'Add to Cart' → complementary 'Skip to main'"

═══ STYLE ═══
- The THREE windows must look like real browser windows (simplified)
- The page content should look like a real e-commerce site (clean, modern)
- The KEY POINT is that Low and Base look VISUALLY IDENTICAL but the DOM is different
- Red annotations on Low window should be overlaid (like code review comments)
- Green annotations on High window should be overlaid similarly
- Clean, academic style — no excessive decoration
- All text legible at print size
```

## Iteration Notes
- The visual identity between Base and Low is THE key point — emphasize "looks the same, DOM is different"
- If the browser mockups are too detailed, simplify the page content
- The bottom strip showing a11y tree differences is optional but powerful
- Consider making this a full-page figure (single column, tall) for maximum impact
- Alternative: show the actual a11y tree text side-by-side instead of browser mockups
