def getPaginationString(_page, totalitems, limit, adjacents, targetpage, pagestring):
    def ceil(x,y):
        m = x%y
        return x/y + 1 if m > 0 else x/y

    if not adjacents: adjacents = 1
    if not limit: limit = 5
    if not _page: _page = 1

    _page = int(_page)
    limit = int(limit)
    adjacents = int(adjacents)
    margin = "3px"
    padding = "3px"

    prev = _page - 1
    _next = _page + 1
    lastpage = ceil(int(totalitems), limit)

    lpm1 = lastpage - 1
    pagination = ""
    if lastpage > 1:
        pagination += "<div class='pagination'"
        if margin or padding:
            pagination += " style='"
            if margin: pagination += "margin: "+margin
            if padding: pagination += "padding: "+padding
            pagination +=  "'"
        pagination += ">"

        pagination += "<a href='" + targetpage + pagestring + "1'>First</a>"
        if _page > 1:
            pagination += "<a href='" + "%s%s%s"%(targetpage , pagestring , prev) + "'>&laquo;previous</a>"
        else:
            pagination += "<span class=\"disabled\">&laquo;prev</span>"
        if (lastpage < (7 + (adjacents * 2))):
            counter = 1
            while (counter < lastpage):
                if counter == _page:
                    pagination += "<span class=\"current\">%s</span>"%counter
                else:
                    pagination += "<a href=\""+ "%s%s%s"%(targetpage, pagestring, counter) + "\">%s</a>"%counter
                counter += 1
        elif (lastpage > (7 +(adjacents * 2))): # enough pages to hide some
            # close to beginning; only hide later page
            if (_page < 1 + (adjacents * 3)):
                counter = 1
                while (counter < (4 + (adjacents * 2))):
                    if counter == _page:
						pagination += "<span class=\"current\">%s</span>"%counter
                    else:
						pagination += "<a href=\""+ "%s%s%s"%(targetpage, pagestring, counter) + "\">%s</a>"%counter
                    counter += 1
            elif (lastpage -(adjacents *2) > _page and _page > (adjacents *2)):
                counter = _page - adjacents
                while (counter < _page + adjacents):
                    if counter == _page:
						pagination += "<span class=\"current\">%s</span>"%counter
                    else:
						pagination += "<a href=\""+ "%s%s%s"%(targetpage, pagestring, counter) + "\">%s</a>"%counter
                    counter += 1
            # close to end;  only hide early pages
            else:
                counter = lastpage - (1 + (adjacents *3))
                while (counter < lastpage):
                    if counter == _page:
						pagination += "<span class=\"current\">%s</span>"%counter
                    else:
						pagination += "<a href=\""+ "%s%s%s"%(targetpage, pagestring, counter) + "\">%s</a>"%counter
                    counter += 1

        #next button
        if (_page < counter - 1):
			pagination += "<a href=\""+ targetpage + pagestring + "%s"%_next + "\">next&raquo;</a>"
        else:
			pagination += "<span class=\"disabled\">next&raquo;</span>"
        pagination += "<a href=\"" + "%s%s%s"%(targetpage, pagestring, lastpage) + "\">"+ "Last" + "</a>"
        pagination += " "+"%s"%_page +" of "+"%s"%lastpage+" Pages  </div>\n"
    return pagination

def lit(**keywords):
	return keywords

def countquery(dbcon, dic):
    if not dic:
        return None
    if 'fields' not in dic or 'relations' not in dic:
        return None
    sql = "SELECT COUNT(*) AS c FROM %s" % dic['relations']
    if (dic.get('criteria',None)):
        sql += " WHERE %(criteria)s" % dic
    res = dbcon.query(sql)
    if res: return res[0]['c']
    return 0

def doquery(dbcon, dic):
    if not dic: return None
    if 'fields' not in dic or 'relations' not in dic:
        return None
    default_offset = 0
    default_limit = 5
    #build the query
    sql = "SELECT %(fields)s FROM %(relations)s " % dic
    if (dic.get('criteria',None)):
        sql += " WHERE %(criteria)s " % dic
    if (dic.get('order', None)):
        sql += " ORDER BY %(order)s " % dic
    if (dic.get('offset',None)):
        sql += " OFFSET %(offset)s " % dic
    if (dic.get('limit',None)):
        sql += " LIMIT %(limit)s " % dic
    res = dbcon.query(sql)
    return res
