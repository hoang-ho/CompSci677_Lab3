import json 

# this is a helper function to construct the initial log file
def add_data():
    data = {}
    data["add"] = [{
            "id": 1,
            "title": "How to get a good grade in 677 in 20 minutes a day.",
            "topic": "distributed systems",
            "stock": 1000,
            "cost": 1
        },
        {
            "id": 2,
            "title": "RPCs for Dummies.",
            "topic": "distributed systems",
            "stock": 1000,
            "cost": 10
        },
        {
            "id": 3,
            "title": "Xen and the Art of Surviving Graduate School.",
            "topic": "graduate school",
            "stock": 1000,
            "cost": 100
        },
        {
            "id": 4,
            "title": "Cooking for the Impatient Graduate Student.",
            "topic": "graduate school",
            "stock": 1000,
            "cost": 1000
        }]

    data["query"] = []
    data["update"] = []

    fw = open("logfile.json", "w") 
    json.dump(data, fw)
    fw.close()
        

if __name__ == "__main__":
    add_data()