"""
Generates a SAMPLE dataset (books.csv + ratings.csv) so the project runs offline.

* Books: ~90 real, well-known titles with short ORIGINAL descriptions written for this project.
* Ratings: SYNTHETIC. 400 imaginary readers with genre tastes rate books with noise.
  (The structure resembles real data, so the recommender and evaluation behave sensibly.)

For the real public dataset (Goodbooks-10k) see docs/02_dataset_and_ml.md and ml/preprocess.py.
Run:  python -m ml.make_sample_data
"""
import os
import random
import pandas as pd

BOOKS = [
# title | author | year | genres | description
("The Hobbit", "J.R.R. Tolkien", 1937, "Fantasy;Adventure", "A comfortable hobbit is swept into a quest with dwarves to reclaim a mountain treasure guarded by a dragon."),
("The Fellowship of the Ring", "J.R.R. Tolkien", 1954, "Fantasy;Adventure", "A small group sets out to destroy a powerful ring before a dark lord can reclaim it."),
("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", 1997, "Fantasy;Young Adult", "An orphan discovers he is a wizard and begins his first year at a school of magic."),
("Harry Potter and the Chamber of Secrets", "J.K. Rowling", 1998, "Fantasy;Young Adult", "A hidden chamber at the wizard school is opened and students begin to be petrified."),
("A Game of Thrones", "George R.R. Martin", 1996, "Fantasy;Adventure", "Noble families fight for a throne while an ancient threat gathers in the frozen north."),
("The Name of the Wind", "Patrick Rothfuss", 2007, "Fantasy;Adventure", "A gifted young musician and magician tells the story of how he became a legend."),
("The Way of Kings", "Brandon Sanderson", 2010, "Fantasy;Adventure", "Warriors, scholars and slaves are drawn into a war on a world scoured by storms."),
("Mistborn: The Final Empire", "Brandon Sanderson", 2006, "Fantasy;Adventure", "A street thief learns to use metal-fuelled magic to overthrow an immortal ruler."),
("The Lion, the Witch and the Wardrobe", "C.S. Lewis", 1950, "Fantasy;Young Adult", "Four children step through a wardrobe into a land trapped in endless winter."),
("American Gods", "Neil Gaiman", 2001, "Fantasy;Mystery", "A released convict becomes the bodyguard of a mysterious man caught in a war between old and new gods."),
("Dune", "Frank Herbert", 1965, "Science Fiction;Adventure", "A noble family takes control of a desert planet that holds the most valuable substance in the universe."),
("Foundation", "Isaac Asimov", 1951, "Science Fiction", "A mathematician predicts the fall of a galactic empire and creates a plan to shorten the dark age."),
("Ender's Game", "Orson Scott Card", 1985, "Science Fiction;Young Adult", "A gifted child is trained in a military school to defend humanity against an alien threat."),
("Neuromancer", "William Gibson", 1984, "Science Fiction;Thriller", "A washed-up hacker is hired for a final job inside a vast computer network."),
("The Martian", "Andy Weir", 2011, "Science Fiction;Adventure", "An astronaut stranded on Mars uses science and humour to survive until rescue."),
("Project Hail Mary", "Andy Weir", 2021, "Science Fiction;Adventure", "A lone astronaut wakes up on a ship with no memory and must save the Earth."),
("The Hitchhiker's Guide to the Galaxy", "Douglas Adams", 1979, "Science Fiction;Classics", "An ordinary man is whisked off Earth moments before its demolition and travels the galaxy."),
("Ready Player One", "Ernest Cline", 2011, "Science Fiction;Adventure", "In a bleak future, a teenager hunts for a hidden prize inside a massive virtual world."),
("The Three-Body Problem", "Liu Cixin", 2008, "Science Fiction;Thriller", "A secret military project makes contact with a civilisation on the brink of collapse."),
("Fahrenheit 451", "Ray Bradbury", 1953, "Dystopian;Classics;Science Fiction", "In a society where books are burned, a fireman begins to question his work."),
("1984", "George Orwell", 1949, "Dystopian;Classics", "A man in a totalitarian state under constant surveillance tries to think for himself."),
("Brave New World", "Aldous Huxley", 1932, "Dystopian;Classics;Science Fiction", "An engineered society of comfort and conditioning is challenged by a visitor from outside."),
("The Hunger Games", "Suzanne Collins", 2008, "Dystopian;Young Adult;Adventure", "A teenage girl volunteers to fight in a televised contest where only one survives."),
("Divergent", "Veronica Roth", 2011, "Dystopian;Young Adult", "In a city divided into factions by virtue, a teenager discovers she does not fit any of them."),
("The Handmaid's Tale", "Margaret Atwood", 1985, "Dystopian;Classics", "In a repressive regime, women are stripped of rights and assigned roles by fertility."),
("The Giver", "Lois Lowry", 1993, "Dystopian;Young Adult", "A boy in a seemingly perfect community is chosen to receive the memories of the past."),
("Gone Girl", "Gillian Flynn", 2012, "Thriller;Mystery", "On a couple's anniversary the wife disappears and suspicion falls on her husband."),
("The Girl with the Dragon Tattoo", "Stieg Larsson", 2005, "Thriller;Mystery", "A journalist and a gifted hacker investigate a decades-old disappearance in a wealthy family."),
("The Da Vinci Code", "Dan Brown", 2003, "Thriller;Mystery", "A symbologist races through Europe to decode clues hidden in famous artworks."),
("Angels & Demons", "Dan Brown", 2000, "Thriller;Mystery", "A professor is called to decipher a threat from an ancient secret society against the Vatican."),
("The Silence of the Lambs", "Thomas Harris", 1988, "Thriller;Horror", "A young agent seeks help from an imprisoned killer to catch another murderer."),
("The Girl on the Train", "Paula Hawkins", 2015, "Thriller;Mystery", "A commuter becomes entangled in a missing-person case she glimpses from her window."),
("Big Little Lies", "Liane Moriarty", 2014, "Mystery;Thriller", "Secrets at a school trivia night lead to a shocking incident among three mothers."),
("And Then There Were None", "Agatha Christie", 1939, "Mystery;Classics", "Ten strangers on an island are accused of past crimes and begin to die one by one."),
("Murder on the Orient Express", "Agatha Christie", 1934, "Mystery;Classics", "A famous detective investigates a murder aboard a snowbound luxury train."),
("The Hound of the Baskervilles", "Arthur Conan Doyle", 1902, "Mystery;Classics", "Sherlock Holmes looks into a legendary spectral hound haunting a country estate."),
("Sherlock Holmes: A Study in Scarlet", "Arthur Conan Doyle", 1887, "Mystery;Classics", "The first meeting of a detective and his doctor companion over a baffling murder."),
("In the Woods", "Tana French", 2007, "Mystery;Thriller", "A detective haunted by his own childhood investigates a child's murder in the same woods."),
("The Cuckoo's Calling", "Robert Galbraith", 2013, "Mystery;Thriller", "A private investigator re-examines the apparent suicide of a famous model."),
("Pride and Prejudice", "Jane Austen", 1813, "Romance;Classics", "A witty young woman and a proud gentleman misjudge each other in Regency England."),
("Jane Eyre", "Charlotte Bronte", 1847, "Romance;Classics", "An orphaned governess falls for her brooding employer and uncovers his secret."),
("Emma", "Jane Austen", 1815, "Romance;Classics", "A confident matchmaker meddles in the love lives of her neighbours."),
("Outlander", "Diana Gabaldon", 1991, "Romance;Historical Fiction;Fantasy", "A nurse is thrown back in time to eighteenth-century Scotland and into a new love."),
("The Notebook", "Nicholas Sparks", 1996, "Romance", "An elderly man reads a love story from a notebook to a woman with failing memory."),
("Me Before You", "Jojo Moyes", 2012, "Romance", "A cheerful woman becomes a caregiver to a bitter man and changes both their lives."),
("The Fault in Our Stars", "John Green", 2012, "Romance;Young Adult", "Two teenagers who meet in a cancer support group fall in love."),
("Twilight", "Stephenie Meyer", 2005, "Romance;Fantasy;Young Adult", "A teenage girl moves to a rainy town and falls for a mysterious vampire classmate."),
("The Kite Runner", "Khaled Hosseini", 2003, "Historical Fiction;Classics", "A man returns to Afghanistan to atone for a childhood betrayal."),
("The Book Thief", "Markus Zusak", 2005, "Historical Fiction;Young Adult", "A girl in Nazi Germany steals books and shares them with those hiding in her basement."),
("All the Light We Cannot See", "Anthony Doerr", 2014, "Historical Fiction", "A blind French girl and a German boy's paths cross during the Second World War."),
("The Pillars of the Earth", "Ken Follett", 1989, "Historical Fiction;Adventure", "Builders, monks and nobles are entangled in constructing a cathedral in medieval England."),
("Wolf Hall", "Hilary Mantel", 2009, "Historical Fiction", "The rise of a blacksmith's son to power in the court of Henry VIII."),
("The Nightingale", "Kristin Hannah", 2015, "Historical Fiction;Romance", "Two sisters in occupied France take different paths to survive and resist."),
("Sapiens", "Yuval Noah Harari", 2011, "Non-Fiction;History", "A sweeping history of how humans came to dominate the planet."),
("Homo Deus", "Yuval Noah Harari", 2015, "Non-Fiction;History;Science Fiction", "A look at how technology and data may reshape the future of humanity."),
("A Brief History of Time", "Stephen Hawking", 1988, "Non-Fiction;Science", "An accessible tour of black holes, the Big Bang and the nature of time."),
("Cosmos", "Carl Sagan", 1980, "Non-Fiction;Science", "A celebration of the universe and humanity's quest to understand it."),
("The Selfish Gene", "Richard Dawkins", 1976, "Non-Fiction;Science", "Evolution viewed from the perspective of genes rather than organisms."),
("Guns, Germs, and Steel", "Jared Diamond", 1997, "Non-Fiction;History", "An argument on why some societies developed power and technology before others."),
("Thinking, Fast and Slow", "Daniel Kahneman", 2011, "Non-Fiction;Self-Help;Science", "How two systems of thought shape our judgments and decisions."),
("Educated", "Tara Westover", 2018, "Biography;Non-Fiction", "A woman raised by survivalists teaches herself enough to reach a university."),
("Becoming", "Michelle Obama", 2018, "Biography;Non-Fiction", "A memoir of growing up in Chicago and life in the White House."),
("Steve Jobs", "Walter Isaacson", 2011, "Biography;Non-Fiction", "A biography of the co-founder of Apple based on interviews with him and those around him."),
("The Diary of a Young Girl", "Anne Frank", 1947, "Biography;Historical Fiction;Classics", "A teenage girl's diary written while hiding from persecution in Amsterdam."),
("Long Walk to Freedom", "Nelson Mandela", 1994, "Biography;Non-Fiction;History", "The autobiography of the anti-apartheid leader and first democratic president of South Africa."),
("Wings of Fire", "A.P.J. Abdul Kalam", 1999, "Biography;Non-Fiction", "The life story of a scientist from a small town who became a nation's president."),
("Atomic Habits", "James Clear", 2018, "Self-Help;Non-Fiction", "A practical system for building good habits and breaking bad ones through small changes."),
("The 7 Habits of Highly Effective People", "Stephen R. Covey", 1989, "Self-Help;Non-Fiction", "A principle-centred approach to personal and professional effectiveness."),
("How to Win Friends and Influence People", "Dale Carnegie", 1936, "Self-Help;Non-Fiction;Classics", "Timeless advice on communication, empathy and building relationships."),
("The Power of Now", "Eckhart Tolle", 1997, "Self-Help;Non-Fiction", "A guide to living in the present moment and quieting the mind."),
("Deep Work", "Cal Newport", 2016, "Self-Help;Non-Fiction", "Why focused, distraction-free work is rare and valuable and how to cultivate it."),
("Rich Dad Poor Dad", "Robert Kiyosaki", 1997, "Self-Help;Non-Fiction", "Lessons about money and investing contrasted through two father figures."),
("The Alchemist", "Paulo Coelho", 1988, "Adventure;Classics;Self-Help", "A shepherd boy travels in search of treasure and learns to follow his dreams."),
("Man's Search for Meaning", "Viktor Frankl", 1946, "Self-Help;Biography;Non-Fiction", "A psychiatrist reflects on finding purpose while surviving concentration camps."),
("Dracula", "Bram Stoker", 1897, "Horror;Classics", "A group of friends hunts a Transylvanian count who has come to England."),
("Frankenstein", "Mary Shelley", 1818, "Horror;Classics;Science Fiction", "A scientist creates a living being and is horrified by what he has made."),
("The Shining", "Stephen King", 1977, "Horror;Thriller", "A family caretaking an isolated hotel in winter faces a growing malevolent presence."),
("It", "Stephen King", 1986, "Horror;Thriller", "A group of friends return to their hometown to face an ancient shape-shifting evil."),
("Pet Sematary", "Stephen King", 1983, "Horror", "A grieving father uses a burial ground with terrifying consequences."),
("The Haunting of Hill House", "Shirley Jackson", 1959, "Horror;Classics", "Paranormal investigators spend a summer in a house with a disturbing history."),
("To Kill a Mockingbird", "Harper Lee", 1960, "Classics;Historical Fiction", "A young girl watches her lawyer father defend a Black man accused in a small southern town."),
("The Great Gatsby", "F. Scott Fitzgerald", 1925, "Classics;Romance", "A mysterious millionaire's obsession with a lost love in the Jazz Age."),
("Moby-Dick", "Herman Melville", 1851, "Classics;Adventure", "A captain's obsessive hunt for a white whale."),
("Great Expectations", "Charles Dickens", 1861, "Classics", "An orphan rises in society thanks to a secret benefactor."),
("The Catcher in the Rye", "J.D. Salinger", 1951, "Classics;Young Adult", "A disillusioned teenager wanders New York after being expelled from school."),
("Lord of the Flies", "William Golding", 1954, "Classics;Adventure;Dystopian", "Stranded schoolboys descend into savagery on a deserted island."),
("Crime and Punishment", "Fyodor Dostoevsky", 1866, "Classics;Mystery", "A poor student commits a murder and is consumed by guilt."),
("The Hunchback of Notre-Dame", "Victor Hugo", 1831, "Classics;Historical Fiction;Romance", "A bell-ringer, a poet and a priest are bound together by a gypsy dancer in medieval Paris."),
("Treasure Island", "Robert Louis Stevenson", 1883, "Adventure;Classics;Young Adult", "A boy finds a treasure map and sets sail with pirates."),
("The Count of Monte Cristo", "Alexandre Dumas", 1844, "Adventure;Classics;Historical Fiction", "A wrongly imprisoned sailor escapes and plans an elaborate revenge."),
("Life of Pi", "Yann Martel", 2001, "Adventure;Historical Fiction", "A boy survives a shipwreck adrift on a lifeboat with a Bengal tiger."),
("Percy Jackson: The Lightning Thief", "Rick Riordan", 2005, "Fantasy;Young Adult;Adventure", "A boy learns he is the son of a Greek god and is accused of stealing Zeus's lightning bolt."),
("Eragon", "Christopher Paolini", 2002, "Fantasy;Young Adult;Adventure", "A farm boy finds a dragon egg and is pulled into a war against a tyrant king."),
("The Maze Runner", "James Dashner", 2009, "Dystopian;Young Adult;Science Fiction", "A boy wakes in a walled maze with other teenagers and no memory."),
("Wonder", "R.J. Palacio", 2012, "Young Adult;Classics", "A boy with a facial difference starts school for the first time."),
("The Midnight Library", "Matt Haig", 2020, "Fantasy;Self-Help", "Between life and death a woman explores the lives she might have lived."),
("Where the Crawdads Sing", "Delia Owens", 2018, "Mystery;Romance", "A girl raised alone in the marshes becomes a suspect in a local murder."),
("The Silent Patient", "Alex Michaelides", 2019, "Thriller;Mystery", "A woman stops speaking after shooting her husband and a therapist is determined to understand why."),
("The Subtle Art of Not Giving a F*ck", "Mark Manson", 2016, "Self-Help;Non-Fiction", "A blunt counter-intuitive guide to choosing what truly matters."),
]
GENRES = sorted({g for b in BOOKS for g in b[3].split(";")})


def build(seed=42, n_users=400, out_dir="data/raw"):
    rng = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)
    books = pd.DataFrame(
        [(i + 1, t, a, y, g, d, "") for i, (t, a, y, g, d) in enumerate(BOOKS)],
        columns=["book_id", "title", "authors", "original_publication_year", "genres", "description", "image_url"],
    )
    quality = {b: rng.uniform(-0.4, 0.6) for b in books.book_id}      # hidden book quality
    pop = {b: rng.uniform(0.15, 1.0) for b in books.book_id}          # how widely read
    book_genres = {r.book_id: r.genres.split(";") for r in books.itertuples()}
    rows = []
    for u in range(1, n_users + 1):
        liked = set(rng.sample(GENRES, rng.randint(2, 3)))
        disliked = set(rng.sample([g for g in GENRES if g not in liked], 2))
        n_read = rng.randint(12, 40)
        for b in rng.sample(list(books.book_id), n_read):
            if rng.random() > pop[b] + 0.35:       # popular books are read more often
                continue
            g = set(book_genres[b])
            affinity = 0.9 * len(g & liked) - 0.8 * len(g & disliked)
            score = 3.2 + affinity + quality[b] + rng.gauss(0, 0.6)
            rows.append((u, b, int(min(5, max(1, round(score))))))
    ratings = pd.DataFrame(rows, columns=["user_id", "book_id", "rating"])
    books.to_csv(f"{out_dir}/books.csv", index=False)
    ratings.to_csv(f"{out_dir}/ratings.csv", index=False)
    print(f"Sample dataset written: {len(books)} books, {ratings.user_id.nunique()} users, {len(ratings)} ratings")


if __name__ == "__main__":
    build()
