
##
##Inspired by Nicolai Swift: https://medium.com/@nicholas.w.swift/easy-a-star-pathfinding-7e6689c7f7b2
##

# coding=utf-8

from __future__ import print_function
import matplotlib.pyplot as plt

import numpy as np
np.set_printoptions(threshold=np.inf, linewidth=300)
import pandas as pd
import time
from PIL import Image

from Map import Map_Obj

class Node():
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position


def astar(maze, start, end):
    """Returns a list of tuples as a path from the given start to the given end in the given maze"""

    # Create start and end node
    start_node = Node(None, start)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end)
    end_node.g = end_node.h = end_node.f = 0

    #Create a object
    MapObj = Map_Obj()

    # Initialize both open and closed list
    open_list = []
    closed_list = []

    # Add the start node
    open_list.append(start_node)

    # Loop until you find the end
    while len(open_list) > 0:

        # Get the current node through itterating open_lsit after the node with the lowest f
        current_node = open_list[0]
        current_index = 0
        for index, item in enumerate(open_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index

        # Pop current off open list, add to closed list
        open_list.pop(current_index)
        closed_list.append(current_node)

        # Found the goal

        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1] # Return reversed path

        # Generate children
        children = []
        for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]: # four vardinal directions: just possible to go horizontally or vertically

            # Get node position
            node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

            # Make sure within range/not outside the x by y fram of samfundet
            if node_position[0] > (len(maze) - 1) or node_position[0] < 0 or node_position[1] > (len(maze[len(maze)-1]) -1) or node_position[1] < 0:
                continue

            # Make sure walkable terrain
            if maze[node_position[0]][node_position[1]] == -1:
                continue

            # Create new node (parrent, position)
            new_node = Node(current_node, node_position)


            # vertification variable
            vertification = 1;

            # Child is already on the closed list
            for closed_child in closed_list:
                if new_node == closed_child:
                    vertification = 0

            # Append
            if vertification == 1:
                children.append(new_node)


        # Loop through children
        for child in children:

            # Create the f, g, and h values
            child.g = current_node.g + MapObj.get_cell_value(child.position)
            child.h = (abs(child.position[0] - end_node.position[0])) + (abs(child.position[1] - end_node.position[1]))  #manhatten distance
            child.f = child.g + child.h

            # vertification and index variable
            vertification = 1;
            index = 0

            for open_node in open_list:
                # Child is already in the open list
                if child == open_node and child.g >= open_node.g:
                    vertification = 0
                #or we have found a shorter path from start to child
                elif child == open_node and child.g < open_node.g:
                    open_list.pop(index)
                    closed_list.append(open_node)
                index += 1

            # Add the child to the open list
            if vertification == 1:
                open_list.append(child)


def main():

    #Object
    MapObj = Map_Obj()

    #parameters needed
    mazeInt, mazeStr = MapObj.get_maps()
    start = MapObj.get_start_pos()
    end = MapObj.get_end_goal_pos()

    #path from start- to end-point
    path = astar(mazeInt,start,end)

    #makeing the cells that the path includes a unidentified character, thus becomes every pathcell yellow
    for point in path:
        MapObj.set_cell_value(point, ' X ')

    MapObj.show_map()


if __name__=="__main__":
	main()
