import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("book_dataset.csv")
features = ['title', 'genre', 'author']


def combine_features(row):
    return row['title'] + " " + row['genre'] + " " + row["author"]


for feature in features:
    df[feature] = df[feature].fillna('')  # filling all NaNs with blank string

df["combined_features"] = df.apply(combine_features, axis=1)  # applying combined_features() method over each rows of dataframe and storing the combined string in “combined_features” column

cv = CountVectorizer()  # creating new CountVectorizer() object
count_matrix = cv.fit_transform(df["combined_features"])  # feeding combined strings(book contents) to CountVectorizer() object
cosine_sim = cosine_similarity(count_matrix)


def get_title_from_index(index):
    return df[df.index == index].values[0]


def get_index_from_title(title):
    return df[df.title == title].index.values[0]


def get_index_from_author(author):
    return df[df.author == author].index.values[0]


def recommendation_generator(title, author):
    similar_books_by_author = list(enumerate(cosine_sim[get_index_from_author(author)]))
    similar_books_by_title = list(enumerate(cosine_sim[get_index_from_title(title)]))

    x, y = sorted(similar_books_by_title, key=lambda x: x[1], reverse=True)[1:6], sorted(similar_books_by_author, key=lambda x: x[1], reverse=True)[1:6]

    title_recommendation = []
    author_recommendation = []

    for i, j in zip(x, y):
        title_recommendation.append(list(get_title_from_index(i[0]))[:3])
        author_recommendation.append(list(get_title_from_index(j[0]))[:3])

    return title_recommendation + author_recommendation






