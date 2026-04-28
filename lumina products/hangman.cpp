#include <iostream>
#include <string>
#include <ctime>
#include <cstdlib>

// Function to draw the hangman's gallows
void drawGallows(int incorrectGuesses) {
    switch (incorrectGuesses) {
        case 0:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            break;
        case 1:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            break;
        case 2:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << " |   | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            break;
        case 3:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << "/|   | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            break;
        case 4:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << "/|\\  | \n";
            std::cout << "     | \n";
            std::cout << "     | \n";
            break;
        case 5:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << "/|\\  | \n";
            std::cout << "/    | \n";
            std::cout << "     | \n";
            break;
        case 6:
            std::cout << " +---+ \n";
            std::cout << " |   | \n";
            std::cout << " O   | \n";
            std::cout << "/|\\  | \n";
            std::cout << "/ \\  | \n";
            std::cout << "     | \n";
            break;
    }
}

int main() {
    // Seed the random number generator
    srand(time(0));

    // List of words to guess from
    std::string words[] = {"apple", "banana", "cherry", "date", "elderberry"};
    int wordIndex = rand() % 5;

    // The word to guess
    std::string word = words[wordIndex];

    // The guessed word
    std::string guessedWord(word.size(), '_');

    // Number of incorrect guesses
    int incorrectGuesses = 0;

    // Game loop
    while (guessedWord != word && incorrectGuesses < 6) {
        // Draw the gallows
        drawGallows(incorrectGuesses);

        // Display the guessed word
        std::cout << "\nWord: " << guessedWord << "\n";

        // Get the user's guess
        char guess;
        std::cout << "Guess a letter: ";
        std::cin >> guess;

        // Check if the guess is in the word
        bool correctGuess = false;
        for (int i = 0; i < word.size(); i++) {
            if (word[i] == guess) {
                guessedWord[i] = guess;
                correctGuess = true;
            }
        }

        // If the guess is incorrect, increment the incorrect guesses counter
        if (!correctGuess) {
            incorrectGuesses++;
        }
    }

    // Display the result
    if (guessedWord == word) {
        std::cout << "\nCongratulations, you won! The word was " << word << ".\n";
    } else {
        std::cout << "\nSorry, you lost. The word was " << word << ".\n";
    }

    return 0;
}
