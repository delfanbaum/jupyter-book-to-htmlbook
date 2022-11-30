import re
import logging
from bs4 import NavigableString  # type: ignore


def process_code(chapter):
    """
    Turn rendered <pre> blocks into appropriately marked-up HTMLBook
    """

    cell_number = 0
    highlight_divs = chapter.find_all(class_="highlight")

    for div in highlight_divs:
        try:
            parent_classes = str(div.parent["class"])

            # apply `data-type` attribute
            pre_tag = div.pre
            pre_tag["data-type"] = "programlisting"

            # remove existing span classes
            for span in pre_tag.find_all('span'):
                del span['class']

            # add language info if available
            if (  # handle R, use `find` for `%%` since we only want it if it's
                  # the very first span tag
                    pre_tag.find('span', string="%%") and
                    pre_tag.find_all('span', string="R")
               ):
                pre_tag["data-code-language"] = "r"
                # remove possibly confusing parent classes
                del div.parent['class']
                # remove extraneous rpy2 flags on first element (thus "find")
                pre_tag.find('span', string="%%").decompose()
                pre_tag.find('span', string="R").decompose()

            # handle python
            elif "python" in parent_classes:
                pre_tag["data-code-language"] = "python"

            # apply numbering
            cell_number = number_codeblock(pre_tag, cell_number)

        except TypeError:
            logging.warning(f"Unable to apply cell numbering to {div}")

        except KeyError:
            logging.warning(f"Unable to apply cell numbering to {div}")

    return chapter


def number_codeblock(pre_block, cell_number):
    """
    Adds numbering markers (`In [##]: ` or `Out[##]: `) to cell blocks

    Note that BeautifulSoup modifies elements in place, so instead of
    returning the pre_block element, we're only returning the cell_number
    to be used in subsequent cells.
    """

    # grandparent of highlight div contains in/out information
    grandparent = pre_block.parent.parent.parent

    if "cell_input" in str(grandparent["class"]):
        in_block = True
        cell_number += 1
        marker = f"In [{cell_number}]: "
    elif (
            "cell_output" in grandparent["class"] and
            # ensure we're not in a hidden-input cell
            "tag_hide-input" not in grandparent.parent["class"]
         ):
        in_block = False
        marker = f"Out[{cell_number}]: "
    else:
        return cell_number

    # insert marker
    pre_block.insert(0, marker)

    # calculate additional indent
    indent = ' ' * len(marker)

    # update tab alignment
    for element in pre_block.contents:
        if type(element) == NavigableString:
            if re.match(r'\n\s*', element):
                element.insert_after(indent)
            elif not in_block:
                # out blocks won't have spans put into them willy-nilly
                # so a "brute force" approach to indentation works fine
                element.replace_with(element.replace('\n', f'\n{indent}'))

    return cell_number
