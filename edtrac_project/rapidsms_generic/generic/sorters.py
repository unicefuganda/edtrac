def simple_comparator(column, item1, item2):
    return item1 - item2

class Sorter(object):
    def sort(self, column, object_list, ascending=True):
        raise NotImplementedError("Subclasses of Sorter must implement the sort() method!")

class SimpleSorter(object):
    def sort(self, column, object_list, ascending=True):
        order_by = "%s%s" % ('' if ascending else '-', column)
        return object_list.order_by(order_by)

class QuickSorter(object):
    """
    >>> qs = QuickSorter(comparator = simple_comparator)
    >>> qs.sort('', [3, 1, 4, 5, 6, 9, 2]
    [1, 2, 3, 4, 5, 6, 9]
    """
    def __init__(self, comparator):
        self.comparator = comparator
    
    def sort(self, column, object_list, ascending=True):
        object_list = list(object_list)
        if len(object_list) == 0:
            return object_list
        pivot = int((0 + len(object_list)) / 2.0)
        self.quicksort(column, object_list, ascending, self.comparator, 0, pivot, len(object_list))
        return object_list

    def quicksort(self, column, object_list, ascending, comparator, start, pivot, finish):
        if finish - 1 <= start:
            return
        else:
            swaps = 0
            pivot_obj = object_list[pivot]
            self.swap(object_list, pivot, finish-1)
            store_index = start
            for i in range(start, finish-1):
                comp = comparator(column, object_list[i], pivot_obj)
                if ((comp < 0) and ascending) or ((comp > 0) and (not ascending)):
                    self.swap(object_list, i, store_index)
                    store_index = store_index + 1
                    swaps += 1
            self.swap(object_list, store_index, finish - 1)
            if swaps == 0:
                return            
            self.quicksort(column, object_list, ascending, comparator, start, int((start + store_index) / 2.0), store_index)
            self.quicksort(column, object_list, ascending, comparator, store_index, int((store_index + finish) / 2.0), finish)
            return
    
    def swap(self, object_list, index1, index2):
        temp = object_list[index1]
        object_list[index1] = object_list[index2]
        object_list[index2] = temp

class TupleSorter(object):
    def __init__(self, index):
        self.index = index

    def sort(self, column, object_list, ascending=True):
        return sorted(object_list, key=lambda tuple: tuple[self.index], reverse=(not ascending))

