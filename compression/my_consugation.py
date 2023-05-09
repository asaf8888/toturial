from prediction_model.model_constants import *
from prediction_model.my_model import MyModel, OneStep
import time
from compression.huffman import get_bits_from_file, extract_data_bits, decode_first_token_in_stream
from compression.compression_utils import get_model_probs
from compression.compression_constants import *


def decompress(filepath, model, use_general_model=True):
    if use_general_model:
        model.load_weights(tf.train.latest_checkpoint(general_model_path))
    one_step_model = OneStep(model, vocab)

    states = None

    input_bits = get_bits_from_file(filepath)
    input_data = extract_data_bits(input_bits)
    first_char = chr(int(input_data[:8], 2))
    next_char = tf.constant([first_char])
    output_tokens = [first_char]
    start_index = 8
    while len(input_data) - start_index > 0:
        list_of_probs, states = get_model_probs(one_step_model, next_char, states)
        decoded_token, start_index = decode_first_token_in_stream(list_of_probs, input_data, start_index)
        next_char = tf.constant([decoded_token])
        output_tokens.append(decoded_token)
    output_text = "".join(output_tokens)
    print(output_text)


if __name__ == '__main__':
    decompress("test data/compressed_not_bible", MyModel(vocab_size, embedding_dim, rnn_units))
