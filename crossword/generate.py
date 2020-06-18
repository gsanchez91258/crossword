import sys
import copy
import operator
from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            removed = set()
            for val in self.domains[var]:
                if var.length != len(val):
                    removed.add(val)
            for r in removed:
                self.domains[var].remove(r)
        


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlaps = self.crossword.overlaps #get overlaps
        if overlaps[x, y] == None: #no revisions to be made if no overlaps
            return revised
        else:
            removed = set()
            i, j = overlaps[x,y]
            for xval in self.domains[x]:
                noPoss = True #If no possibility for y given x
                for yval in self.domains[y]:
                    if xval[i] == yval[j]: #if all x at overlap == y at overlap given x, possibility
                        noPoss = False
                if noPoss == True:
                    removed.add(xval) #remove x and mark as revised
                    revised = True 
            for xv in removed:
                self.domains[x].remove(xv)
        return revised


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs == None:
            queue = set()
            overlaps = self.crossword.overlaps
            for key in overlaps:
                if overlaps[key] != None:
                    queue.add(key)
        else:
            queue = arcs
        while len(queue) > 0:
            x, y = queue.pop()
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                for z in self.crossword.neighbors(x) - {y}:
                    queue.add((x, z))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for ass in assignment:
            if assignment[ass] == None:
                return False
        if not all(var in assignment for var in self.crossword.variables):
            return False
        return True


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        temp = set()
        for ass in assignment:
            if ass.length != len(assignment[ass]): #check length of word
                return False
            if assignment[ass] in temp: #check distinct values
                return False
            temp.add(assignment[ass])
            neighbors = self.crossword.neighbors(ass)
            for cheeks in neighbors:
                if cheeks in assignment:
                    if ass is not cheeks:
                        if self.crossword.overlaps[ass, cheeks] is not None: #had to do it to em
                            (i, j) = self.crossword.overlaps[ass, cheeks]
                            a = assignment[ass]
                            b = assignment[cheeks]
                            if a[i] != b[j]:
                                return False
        return True

    def testConsistent(self, var, val, assignment):
        '''
        check to see if assignment is consistent when a variable is added
        '''
        newAssignment = copy.deepcopy(assignment)
        newAssignment[var] = val
        return self.consistent(newAssignment)

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        nd = dict()
        for val in self.domains[var]: #values for var
            n = 0
            for neigh in self.crossword.neighbors(var): #loop through neighbors of var
                if neigh not in assignment: #only if neighbor not in assignment
                    i, j = self.crossword.overlaps[var, neigh]
                    for ndom in self.domains[neigh]: #loop through values in domain of neighbor
                        if val[i] != ndom[j]:
                            n += 1
            nd[val] = n
        nd = {k: v for k, v in sorted(nd.items(), key=lambda item: item[1])}
        return nd

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        remaining = dict()
        for v in self.crossword.variables:
            if v not in assignment:
                rv = len(self.domains[v])
                deg = len(self.crossword.neighbors(v))
                remaining[v] = (rv, deg)
        sorts = sorted(remaining.items(), key = lambda x: x[1][0]) #sort first by remaining values
        sorts = sorted(remaining.items(), key = lambda x: x[1][1], reverse=True) #then sort by descending degrees
        return sorts[0][0]
    

    def inference(self, assignment, var):
        tempDom = copy.deepcopy(self.domains[var])
        arcs = set()
        varr = set()
        inferences = dict()
        for n in self.crossword.neighbors(var):
            if n not in assignment:
                arcs.add((var, n)) #maybe (n, var) ?
                varr.add(n)
        result = self.ac3(arcs)
        if not result:
            self.domains[var] = tempDom
            return None
        for v in varr:
            if len(self.domains[v]) == 1:
                inferences[v] = self.domains[v]
        return inferences

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for val in self.domains[var]:
            newAssignment = copy.deepcopy(assignment)
            newAssignment[var] = val
            if self.consistent(newAssignment):
                #inferences = self.inference(newAssignment, var)
                #tempAss = copy.deepcopy(newAssignment)
                #if inferences is not None:
                #    for i in inferences:
                #        tempAss[i] = inferences[i]
                result = self.backtrack(newAssignment)
                if result is not None:
                    return result
            #tempAss = newAssignment
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
