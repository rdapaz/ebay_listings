# !/usr/bin/env python3
import markdown2
import tidylib
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import argparse
import yaml

# Configuration for GitHub image hosting
GITHUB_USER = "rdapaz"
GITHUB_REPO = "ebay_listings"
GITHUB_BRANCH = "main"

TEMPLATE_MD = """
# {title}

<div class="images-container">
{images}
</div>

{description}

## Payment Policy

* Paypal is preferred
* Direct Bank Deposit is also good!
* Item will be shipped immediately on the same or next business day of receiving full payment

## Shipping Policy

Please note that it may take up to 7 days for shipping as we reserve the right for your payment to clear prior to shipping the goods.

The following freight charges are applicable:

* {postage}

## Returns Policy

No exchange or warranty is offered on these goods but we will make every effort to ensure that you get the item in the same condition as it left our premises.

## Terms & Conditions

By bidding on this item you are offering to enter into a contract with the seller. The winning bidder will enter a contract of sale between themselves and the seller only. We reserve the right not to ship the item until the payment has been received in full and has cleared, and will cancel the sale if full payment is not received within 7 days of the auction ending.

## About Us

We are just getting rid of some of our toys to make room for new toys. We love our toys and take good care of them. We hope you will find something that you like. Thanks for looking!
"""

MODERN_CSS = """
:root {
    --primary-color: #2d3748;
    --secondary-color: #4a5568;
    --accent-color: #3182ce;
    --background-color: #ffffff;
    --text-color: #4a5568;
    --border-color: #e2e8f0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    background: var(--background-color);
}

h1, h2 {
    color: var(--primary-color);
    margin-top: 2rem;
    margin-bottom: 1rem;
    font-weight: 600;
}

h1 {
    font-size: 2rem;
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 0.5rem;
}

h2 {
    font-size: 1.5rem;
}

.images-container {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
    margin: 2rem 0;
    padding: 1rem;
    background: var(--border-color);
    border-radius: 0.5rem;
}

.images-container img {
    max-width: 100%;
    height: auto;
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

ul {
    list-style-type: disc;
    margin-left: 1.5rem;
    margin-bottom: 1.5rem;
}

li {
    margin-bottom: 0.5rem;
}

p {
    margin-bottom: 1rem;
}

.shipping-info {
    background-color: #f7fafc;
    border-left: 4px solid var(--accent-color);
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.25rem;
}

@media (max-width: 640px) {
    body {
        padding: 1rem;
    }

    .images-container {
        flex-direction: column;
    }
}
"""


@dataclass
class Auction:
    """Data class to hold auction information."""
    title: str
    description: str
    override: bool
    photo_1: str
    photo_2: Optional[str]
    out_file: str

    @classmethod
    def from_yaml(cls, data: dict) -> 'Auction':
        """Create an Auction instance from YAML data."""
        description = data.get('description', '')

        # If description is not inline, try to read from file if specified
        if not description and 'description_file' in data:
            try:
                with open(data['description_file'], 'r') as f:
                    description = f.read()
            except FileNotFoundError:
                print(f"Warning: Could not find description file {data['description_file']}")
                description = f"You are bidding on: {data['title']}\n\nHappy bidding and thanks for looking!"

        return cls(
            title=data.get('title', ''),
            description=description,
            override=bool(data.get('override', False)),
            photo_1=data.get('photo_1', ''),
            photo_2=data.get('photo_2'),
            out_file=data.get('out_file', '')
        )


def get_github_raw_url(image_path: str) -> str:
    """Convert a local image path to a GitHub raw URL."""
    if not image_path:
        return ""
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/artefacts/{image_path}"


def generate_image_html(pic1: str, pic2: Optional[str]) -> str:
    """Generate HTML for the images section."""
    images = [f'<img src="{get_github_raw_url(pic1)}" alt="{pic1}">' if pic1 else ""]
    if pic2:
        images.append(f'<img src="{get_github_raw_url(pic2)}" alt="{pic2}">')
    return "\n".join(images)


def generate_html(auction: Auction) -> str:
    """Generate the complete HTML for an auction."""
    postage = ("This item will be delivered by Express Post. If you live in Perth "
               "you can also pick it up. Postage and Handling Costs: $15.00" if auction.override
               else "Not applicable: pick up in Bibra Lake only")

    # Convert markdown content to HTML
    markdown_content = TEMPLATE_MD.format(
        title=auction.title,
        images=generate_image_html(auction.photo_1, auction.photo_2),
        description=auction.description,
        postage=postage
    )
    content_html = markdown2.markdown(markdown_content)

    # Combine with HTML template
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{auction.title} - eBay Listing</title>
        <style>
        {MODERN_CSS}
        </style>
    </head>
    <body>
        {content_html}
    </body>
    </html>
    """

    # Tidy the HTML
    document, errors = tidylib.tidy_document(full_html, options={
        'indent': 1,
        'tab-size': 2,
        'output-xhtml': 0,
        'wrap': 0
    })

    if errors:
        print(f"HTML Tidy reported warnings/errors:\n{errors}")

    return document


def parse_auctions_file(filename: str) -> List[Auction]:
    """Parse the auction data file into a list of Auction objects."""
    auctions = []

    with open(filename, 'r') as f:
        # Load all YAML documents from the file
        yaml_documents = list(yaml.safe_load_all(f))

        for doc in yaml_documents:
            if doc:  # Skip empty documents
                try:
                    auctions.append(Auction.from_yaml(doc))
                except Exception as e:
                    print(f"Error parsing auction entry: {e}")
                    continue

    return auctions


def main():
    parser = argparse.ArgumentParser(description='Generate eBay auction HTML files')
    parser.add_argument('auctions_file', help='Path to the auctions YAML file')
    parser.add_argument('--output-dir', help='Directory for output HTML files', default='.')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        auctions = parse_auctions_file(args.auctions_file)
    except FileNotFoundError:
        print(f"Error: Auctions data file '{args.auctions_file}' not found")
        return
    except Exception as e:
        print(f"Error reading auctions file: {e}")
        return

    for auction in auctions:
        output_file = output_dir / auction.out_file
        try:
            html_content = generate_html(auction)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Generated auction HTML: {output_file}")
        except Exception as e:
            print(f"Error writing output file {output_file}: {e}")


if __name__ == '__main__':
    main()