from collections import Counter
import multiprocessing
import time
from tqdm import tqdm
import logging
logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(levelname)s %(message)s")
log = logging.getLogger()


log.info("Loading spacy with English model. (might take a while!)")
from spacy.en import English
from spacy.symbols import PUNCT
parser = English()
log.info("Done initializing spacy!")


def get_counter_from_line(line):
    line = u" ".join(line.lower().split())
    if not line:
        return Counter()
    parsed_line = parser(line)
    return Counter(
        [token.orth_ for token in parsed_line if token.pos is not PUNCT])

def reducer(l):
    return reduce(lambda a,b:a+b, l)

def create_counter_from_book(book_file_name):
    log.info("Opening book")
    with open(book_file_name, "r") as book:
        log.info("Reading lines using all available cores")
        pool = multiprocessing.Pool()
        counters = pool.map_async(get_counter_from_line, book)
        pool.close
        remaining = counters._number_left
        with tqdm(total=remaining) as pbar:
            while (True):
              if (counters.ready()):
                  counters = counters.get()
                  pbar.update(remaining)
                  break
              new_remaining = counters._number_left
              delta = abs(remaining - new_remaining)
              remaining = new_remaining
              if delta:
                  pbar.update(delta)
              time.sleep(0.5)
        log.info("reducing counters")
        n = 4
        while True:
            pool = multiprocessing.Pool()
            counter_chunks = (counters[i:i+n] for i in xrange(0, len(counters), n))
            counters = pool.map_async(reducer, counter_chunks)
            pool.close()
            remaining = counters._number_left
            with tqdm(total=remaining) as pbar:
                try:
                    while (True):
                        if (counters.ready()):
                            raise Exception
                        new_remaining = counters._number_left
                        delta = abs(remaining - new_remaining)
                        remaining = new_remaining
                        if delta:
                            pbar.update(delta)
                        time.sleep(0.5)
                except:
                    counters = counters.get()
                    pbar.update(remaining)
            if len(counters) < 2:
                return counters[0]

def get_dimension(counter_length):
    import math
    def perfect_sq(n):
        dimension = int(math.sqrt(n))
        if n == dimension ** 2:
            return dimension
    log.info("computing nearest perfect square of {}".format(counter_length))
    while True:
        dimension = perfect_sq(counter_length)
        if dimension:
            log.info("found nearest perfect square: {} with dimension: {}".format(counter_length, dimension))
            return dimension
        counter_length += 1

def save_counter_as_image(counter, output_file_name):
    from PIL import Image
    import numpy
    log.info("now creating image")
    counter_length = len(counter.keys())
    dimension = get_dimension(counter_length)
    image = Image.new("RGB", (dimension, dimension), "white")
    pixels = image.load()
    step = 255.0 / (numpy.mean(counter.values())+2)
    log.info("step size: {}".format(step))
    sorted_counter = sorted(counter.items(), key=lambda item:len(item[0]))
    values = [int(value * step) for key,value in sorted_counter]
    with tqdm(total=dimension * dimension) as pbar:
        for i in range(dimension):
            for j in range(dimension):
                pbar.update(1)
                index = (i * dimension) + j
                if index < len(values):
                    value = values[index]
                    pixels[i,j] = (value, value, value)
    image.save(output_file_name, "PNG")

if __name__ == "__main__":
    import sys
    input_file = sys.argv[1]
    output_file = "output.png"

    log.info("parsing file: {}, outputing to: {}".format(
        input_file, output_file))
    counter = create_counter_from_book(input_file)
    save_counter_as_image(counter, output_file)
    log.info("fin")
